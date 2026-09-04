import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# متغیرهای محیطی حداقلی برای اجرای تست
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("BALE_BOT_TOKEN", "test-token")
os.environ.setdefault("BALE_WEBHOOK_SECRET", "test-secret")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-signing-only")
os.environ.setdefault("SCHEDULER_ENABLED", "false")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models.admin import Admin, AdminRole
from app.core.security import hash_password

TEST_ENGINE = create_engine(
    "sqlite:///./test.db",
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=TEST_ENGINE,
)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=TEST_ENGINE)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=TEST_ENGINE)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def super_admin_token(db_session, client):
    admin = Admin(
        username="admin_test",
        full_name="Test Admin",
        hashed_password=hash_password("StrongPass123"),
        role=AdminRole.SUPER_ADMIN,
        is_active=True,
    )

    db_session.add(admin)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin_test",
            "password": "StrongPass123",
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]
