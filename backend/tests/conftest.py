"""
Shared pytest fixtures for all test modules.
Uses SQLite in-memory DB, mocked S3 (moto), and Celery eager mode.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Must be set before any app imports
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("S3_ENDPOINT_URL", "http://localhost:9000")
os.environ.setdefault("S3_ACCESS_KEY", "test")
os.environ.setdefault("S3_SECRET_KEY", "test")
os.environ.setdefault("S3_BUCKET_UPLOADS", "uploads")
os.environ.setdefault("S3_BUCKET_OUTPUTS", "outputs")
os.environ.setdefault("S3_BUCKET_CODEBASE", "codebase")
os.environ.setdefault("CLAUDE_API", "test-key")
os.environ.setdefault("FRONTEND_ORIGIN", "http://localhost:3000")

from app.db import Base
from app.dependencies import get_db
from app.main import app

SQLALCHEMY_TEST_URL = "sqlite:///./test.db"

engine = create_engine(SQLALCHEMY_TEST_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture()
def registered_user(client):
    """Register and return credentials."""
    payload = {"email": "user@test.com", "password": "Password123!"}
    client.post("/auth/register", json=payload)
    return payload


@pytest.fixture()
def auth_cookies(client, registered_user):
    """Login and return a TestClient that carries auth cookies."""
    resp = client.post("/auth/login", json=registered_user)
    assert resp.status_code == 200
    return client  # TestClient propagates cookies automatically
