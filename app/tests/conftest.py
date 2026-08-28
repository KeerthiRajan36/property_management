import os

os.environ["DATABASE_URL"] = "sqlite:///./test_property_management.db"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_property_management.db"):
        os.remove("./test_property_management.db")


@pytest.fixture()
def client():
    # Context manager form triggers FastAPI startup/shutdown lifespan events
    # (table creation is idempotent; websocket loop registration happens here).
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_token(client):
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin@test.com",
            "password": "admin1234",
            "role": "super_admin",
        },
    )
    resp = client.post(
        "/api/v1/auth/login", json={"email": "admin@test.com", "password": "admin1234"}
    )
    return resp.json()["access_token"]


@pytest.fixture()
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
