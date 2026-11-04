import pytest
import json
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models.auth import User
from app.models.settings import UserSettings, SyncEventJournal
from app.utils.auth_utils import create_access_token
from app.utils.security import get_password_hash


from tests.conftest import TestingSessionLocal

@pytest.fixture(scope="module")
def setup_sync_db():
    db = TestingSessionLocal()
    
    # Clean up test users
    db.query(User).filter(User.email.in_(["sync_alice@example.com", "sync_bob@example.com"])).delete(synchronize_session=False)
    db.commit()

    # Create Alice
    alice = User(
        name="Alice Authenticity",
        email="sync_alice@example.com",
        hashed_password=get_password_hash("SecurePassword123!"),
        is_active=True,
        is_verified=True,
        version=1,
    )
    # Create Bob
    bob = User(
        name="Bob Investigator",
        email="sync_bob@example.com",
        hashed_password=get_password_hash("SecurePassword123!"),
        is_active=True,
        is_verified=True,
        version=1,
    )
    db.add(alice)
    db.add(bob)
    db.commit()
    db.refresh(alice)
    db.refresh(bob)

    alice_token = create_access_token({"sub": alice.email})
    bob_token = create_access_token({"sub": bob.email})
    
    yield {
        "alice": alice,
        "bob": bob,
        "alice_token": alice_token,
        "bob_token": bob_token,
    }
    db.close()


def test_websocket_unauthorized_rejected(setup_sync_db):
    client = TestClient(app)
    # Attempt connecting without token
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws") as ws:
            pass


def test_websocket_invalid_token_rejected(setup_sync_db):
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/api/ws?token=invalid_jwt_token_123") as ws:
            pass


def test_websocket_connect_and_handshake(setup_sync_db):
    client = TestClient(app)
    alice_token = setup_sync_db["alice_token"]
    alice_id = setup_sync_db["alice"].id

    with client.websocket_connect(f"/api/ws?token={alice_token}") as ws:
        msg = ws.receive_json()
        assert msg["event"] == "connected"
        assert msg["user_id"] == alice_id
        assert "server_time" in msg

        # Test ping/pong
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"


def test_settings_get_and_put_concurrency(setup_sync_db):
    client = TestClient(app)
    alice_token = setup_sync_db["alice_token"]
    headers = {"Authorization": f"Bearer {alice_token}"}

    # 1. GET settings
    res = client.get("/api/settings", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "sensitivity_tolerance" in data
    assert "api_key" in data
    assert data["version"] >= 1
    current_ver = data["version"]

    # 2. PUT settings successfully
    update_res = client.put(
        "/api/settings",
        headers=headers,
        json={"sensitivity_tolerance": 85.5, "version": current_ver},
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["sensitivity_tolerance"] == 85.5
    assert updated_data["version"] == current_ver + 1

    # 3. PUT with stale version -> Expect 409 Conflict
    stale_res = client.put(
        "/api/settings",
        headers=headers,
        json={"sensitivity_tolerance": 90.0, "version": current_ver},
    )
    assert stale_res.status_code == 409
    assert "Conflict" in stale_res.json()["detail"]["message"]


def test_profile_update_and_sync_event(setup_sync_db):
    client = TestClient(app)
    alice_token = setup_sync_db["alice_token"]
    headers = {"Authorization": f"Bearer {alice_token}"}

    # Update Alice's name
    res = client.put("/api/auth/profile", headers=headers, json={"name": "Alice SuperUser"})
    assert res.status_code == 200
    user_res = res.json()
    assert user_res["name"] == "Alice SuperUser"
    assert user_res["version"] >= 2


def test_authoritative_sync_state(setup_sync_db):
    client = TestClient(app)
    alice_token = setup_sync_db["alice_token"]
    headers = {"Authorization": f"Bearer {alice_token}"}

    res = client.get("/api/sync/state", headers=headers)
    assert res.status_code == 200
    state = res.json()
    assert "server_time" in state
    assert state["user"]["email"] == "sync_alice@example.com"
    assert "settings" in state
    assert "recent_analyses" in state
    assert "total_analyses" in state


def test_user_data_isolation(setup_sync_db):
    client = TestClient(app)
    alice_token = setup_sync_db["alice_token"]
    bob_token = setup_sync_db["bob_token"]

    # Bob's settings
    bob_headers = {"Authorization": f"Bearer {bob_token}"}
    bob_res = client.get("/api/settings", headers=bob_headers)
    assert bob_res.status_code == 200
    bob_settings = bob_res.json()

    # Alice's sync events should not contain Bob's events
    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    alice_events = client.get("/api/sync/events", headers=alice_headers).json()
    
    for evt in alice_events["events"]:
        assert evt["payload"]["user_id"] == setup_sync_db["alice"].id
