import io
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.auth import User
from app.models.settings import UserSettings, SyncEventJournal
from app.models.analysis import Analysis, AnalysisResult, Notification
from app.utils.auth_utils import create_access_token
from app.utils.security import get_password_hash
from tests.conftest import TestingSessionLocal


@pytest.fixture(scope="module")
def e2e_users():
    db = TestingSessionLocal()
    
    # Clean up prior test runs
    db.query(Notification).delete()
    db.query(AnalysisResult).delete()
    db.query(Analysis).delete()
    db.query(SyncEventJournal).delete()
    db.query(UserSettings).delete()
    db.query(User).filter(User.email.in_(["e2e_alice@deepguard.ai", "e2e_bob@deepguard.ai"])).delete(synchronize_session=False)
    db.commit()

    # Create Alice (Primary dual-device user: Web + Android)
    alice = User(
        name="Alice Authenticity",
        email="e2e_alice@deepguard.ai",
        hashed_password=get_password_hash("StrongSecret123!"),
        is_active=True,
        is_verified=True,
        version=1,
    )
    # Create Bob (Isolated third-party user)
    bob = User(
        name="Bob Outsider",
        email="e2e_bob@deepguard.ai",
        hashed_password=get_password_hash("StrongSecret123!"),
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

    context = {
        "alice_id": alice.id,
        "bob_id": bob.id,
        "alice_token": alice_token,
        "bob_token": bob_token,
    }
    db.close()
    return context


def make_valid_png() -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    img = Image.new("RGB", (128, 128), color=(120, 150, 180))
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_01_upload_image_on_web_appears_in_android(e2e_users):
    """Test 1: Upload an image on the website and verify it appears in Android without refreshing."""
    client = TestClient(app)
    token = e2e_users["alice_token"]

    # Android client is connected via WebSocket
    with client.websocket_connect(f"/api/ws?token={token}") as android_ws:
        init_msg = android_ws.receive_json()
        assert init_msg.get("event") == "connected" or init_msg.get("type") == "connected"

        # Web client uploads an image
        files = {"file": ("sample_web.png", io.BytesIO(make_valid_png()), "image/png")}
        headers = {"Authorization": f"Bearer {token}"}
        upload_resp = client.post("/api/analysis/image", files=files, headers=headers)
        assert upload_resp.status_code in [200, 202]
        analysis_data = upload_resp.json()
        analysis_id = analysis_data["analysis_id"]

        # Android client receives real-time broadcast without manual refresh
        received_events = []
        for _ in range(4):
            try:
                ev = android_ws.receive_json()
                received_events.append(ev.get("event"))
            except Exception:
                break

        assert "media.uploaded" in received_events or "analysis.completed" in received_events

        # Android client queries authoritative scan history
        history_resp = client.get("/api/analysis/history?page=1&page_size=10", headers=headers)
        assert history_resp.status_code == 200
        history_items = history_resp.json()["items"]
        assert any(item["id"] == analysis_id for item in history_items)


def test_02_and_04_upload_and_analyze_on_android_appears_on_web(e2e_users):
    """Test 2 & 4: Upload/analyze media on Android and verify identical scan ID and result on the website."""
    client = TestClient(app)
    token = e2e_users["alice_token"]

    # Web client is connected via WebSocket
    with client.websocket_connect(f"/api/ws?token={token}") as web_ws:
        init_msg = web_ws.receive_json()
        assert init_msg.get("event") == "connected" or init_msg.get("type") == "connected"

        # Android client uploads and analyzes an image
        files = {"file": ("sample_android.png", io.BytesIO(make_valid_png()), "image/png")}
        headers = {"Authorization": f"Bearer {token}"}
        android_upload = client.post("/api/analysis/image", files=files, headers=headers)
        assert android_upload.status_code in [200, 202]
        android_data = android_upload.json()
        analysis_id = android_data["analysis_id"]

        # Web client receives the live events
        received_events = []
        for _ in range(4):
            try:
                ev = web_ws.receive_json()
                received_events.append(ev.get("event"))
            except Exception:
                break

        assert "media.uploaded" in received_events or "analysis.completed" in received_events

        # Web client fetches analysis detail: identical scan ID, prediction, and status
        detail_resp = client.get(f"/api/analysis/{analysis_id}", headers=headers)
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["id"] == analysis_id
        assert detail_data["status"] == "completed"


def test_03_analyze_media_on_web_identical_in_android(e2e_users):
    """Test 3: Media analyzed on website shares identical record and details in Android."""
    client = TestClient(app)
    token = e2e_users["alice_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch recent analyses
    history_resp = client.get("/api/analysis/history?page=1&page_size=5", headers=headers)
    assert history_resp.status_code == 200
    items = history_resp.json()["items"]
    assert len(items) > 0
    target_scan = items[0]

    # Verify both Web and Android see identical fields
    detail_resp = client.get(f"/api/analysis/{target_scan['id']}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == target_scan["id"]
    assert detail["original_filename"] == target_scan["original_filename"]
    assert detail["media_type"] == target_scan["media_type"]


def test_05_update_profile_on_web_syncs_to_android(e2e_users):
    """Test 5: Update the profile on the website and verify the change in Android."""
    client = TestClient(app)
    token = e2e_users["alice_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Android client is connected
    with client.websocket_connect(f"/api/ws?token={token}") as android_ws:
        android_ws.receive_json()

        # Web client fetches current profile version
        me = client.get("/api/auth/me", headers=headers).json()
        current_version = me.get("version", 1)

        # Web updates profile
        new_name = "Alice From Web"
        put_resp = client.put(
            "/api/auth/profile",
            json={"name": new_name, "version": current_version},
            headers=headers
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["name"] == new_name

        # Android client receives real-time profile.updated event
        ev = android_ws.receive_json()
        assert ev["event"] == "profile.updated"
        assert ev["data"]["name"] == new_name


def test_06_update_profile_on_android_syncs_to_web(e2e_users):
    """Test 6: Update the profile on Android and verify the change on the website."""
    client = TestClient(app)
    token = e2e_users["alice_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Web client is connected
    with client.websocket_connect(f"/api/ws?token={token}") as web_ws:
        web_ws.receive_json()

        me = client.get("/api/auth/me", headers=headers).json()
        current_version = me.get("version", 1)

        # Android updates profile
        new_name = "Alice From Android"
        put_resp = client.put(
            "/api/auth/profile",
            json={"name": new_name, "version": current_version},
            headers=headers
        )
        assert put_resp.status_code == 200

        # Web receives event
        ev = web_ws.receive_json()
        assert ev["event"] == "profile.updated"
        assert ev["data"]["name"] == new_name

        # Website authoritative fetch reflects the change
        me_after = client.get("/api/auth/me", headers=headers).json()
        assert me_after["name"] == new_name


def test_07_change_settings_and_notifications_syncs_both_ways(e2e_users):
    """Test 7: Change supported account settings and notification status from either client and verify the other updates."""
    client = TestClient(app)
    token = e2e_users["alice_token"]
    headers = {"Authorization": f"Bearer {token}"}

    with client.websocket_connect(f"/api/ws?token={token}") as client_ws:
        client_ws.receive_json()

        # Update settings (tolerance = 85.0)
        curr_settings = client.get("/api/settings", headers=headers).json()
        settings_ver = curr_settings["version"]
        put_settings = client.put(
            "/api/settings",
            json={"sensitivity_tolerance": 85.0, "api_key": "dg_live_sync_key", "version": settings_ver},
            headers=headers
        )
        assert put_settings.status_code == 200

        ev = client_ws.receive_json()
        assert ev["event"] == "settings.updated"
        assert ev["data"]["sensitivity_tolerance"] == 85.0

        # Mark notification as read
        notifs_resp = client.get("/api/notifications", headers=headers)
        assert notifs_resp.status_code == 200
        notifs = notifs_resp.json()
        if len(notifs) > 0:
            target_id = notifs[0]["id"]
            patch_resp = client.patch(f"/api/notifications/{target_id}/read", headers=headers)
            assert patch_resp.status_code == 200

            notif_ev = client_ws.receive_json()
            assert notif_ev["event"] == "notification.read"


def test_08_delete_media_record_syncs_both_clients(e2e_users):
    """Test 8: Delete a test media record on either client and verify that both reflect the deletion."""
    client = TestClient(app)
    token = e2e_users["alice_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload an item to delete
    files = {"file": ("delete_me.png", io.BytesIO(make_valid_png()), "image/png")}
    upload_res = client.post("/api/analysis/image", files=files, headers=headers).json()
    item_id = upload_res["analysis_id"]

    with client.websocket_connect(f"/api/ws?token={token}") as ws:
        ws.receive_json()

        # Delete the record
        del_resp = client.delete(f"/api/analysis/{item_id}", headers=headers)
        assert del_resp.status_code == 200

        # Verify real-time delete event
        received_events = []
        for _ in range(2):
            try:
                ev = ws.receive_json()
                received_events.append(ev.get("event"))
            except Exception:
                break
        assert "media.deleted" in received_events or "history.updated" in received_events

        # Authoritative scan list no longer contains item_id
        hist = client.get("/api/analysis/history?page=1&page_size=50", headers=headers).json()
        assert all(it["id"] != item_id for it in hist["items"])


def test_09_disconnect_offline_recovery_on_reconnect(e2e_users):
    """Test 9: Disconnect one client, make changes on the other, reconnect and recover every relevant change."""
    client = TestClient(app)
    token = e2e_users["alice_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Client goes OFFLINE (no WebSocket connection)
    # While offline, multiple operations happen on backend
    me = client.get("/api/auth/me", headers=headers).json()
    client.put("/api/auth/profile", json={"name": "Alice Recovered", "version": me.get("version", 1)}, headers=headers)
    curr_settings = client.get("/api/settings", headers=headers).json()
    client.put("/api/settings", json={"sensitivity_tolerance": 90.0, "version": curr_settings["version"]}, headers=headers)

    # Client RECONNECTS and fetches authoritative single-round-trip sync state snapshot
    sync_resp = client.get("/api/sync/state", headers=headers)
    assert sync_resp.status_code == 200
    state = sync_resp.json()
    assert state["user"]["name"] == "Alice Recovered"
    assert state["settings"]["sensitivity_tolerance"] == 90.0
    assert "server_time" in state
    assert "total_analyses" in state


def test_10_dashboard_statistics_and_history_consistency(e2e_users):
    """Test 10: Verify dashboard statistics and scan history remain strictly consistent."""
    client = TestClient(app)
    token = e2e_users["alice_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch history items
    hist = client.get("/api/analysis/history?page=1&page_size=100", headers=headers).json()
    actual_count = hist["total"]

    # Fetch sync state
    sync_state = client.get("/api/sync/state", headers=headers).json()
    assert sync_state["total_analyses"] == actual_count


def test_11_user_data_isolation(e2e_users):
    """Test 11: Verify that one user cannot receive or access another user's private records or real-time events."""
    client = TestClient(app)
    alice_token = e2e_users["alice_token"]
    bob_token = e2e_users["bob_token"]

    alice_headers = {"Authorization": f"Bearer {alice_token}"}
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # Bob connects to WebSocket
    with client.websocket_connect(f"/api/ws?token={bob_token}") as bob_ws:
        bob_ws.receive_json()

        # Alice performs a private action: update her profile
        alice_me = client.get("/api/auth/me", headers=alice_headers).json()
        client.put("/api/auth/profile", json={"name": "Alice Secret", "version": alice_me.get("version", 1)}, headers=alice_headers)

        # Bob pings the socket to check if any message leaked
        bob_ws.send_json({"type": "ping"})
        bob_msg = bob_ws.receive_json()
        # Bob only gets his own pong, never Alice's profile.updated event!
        assert bob_msg["type"] == "pong"

    # Bob attempts to fetch Alice's settings
    bob_settings = client.get("/api/settings", headers=bob_headers).json()
    # Bob has his own settings, completely separate from Alice
    assert bob_settings["api_key"] != "dg_live_sync_key"
