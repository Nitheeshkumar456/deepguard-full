"""
conftest.py — Global pytest fixtures and test configuration for DeepGuard backend.
"""

import os
import sys
import pytest

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base
from app.dependencies import get_db
from app.limiter import limiter

# Disable rate limiting during automated test suite runs
limiter.enabled = False

# Use file-based SQLite test database with all tables created
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), "test_suite.db")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_suite_database():
    """Create all database tables once for the test session, drop on completion."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass


@pytest.fixture(scope="session")
def client():
    """Shared TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    """Provide a fresh database session for direct inspection."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def mock_otp_email(monkeypatch):
    """Prevent outgoing SMTP network calls during test runs by default."""
    monkeypatch.setattr("app.routes.auth.send_otp_email", lambda **kwargs: True)
