import os

os.environ.setdefault("JWT_SECRET", "test-secret-only-never-for-deployment-123456789")
os.environ.setdefault("DEMO_PASSWORD", "test-password-12345")
os.environ["AGENT_MODE"] = "offline"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.main import app, limiter
from backend.db.models import Base
from backend.db.seed import seed
from backend.db.session import get_db


@pytest.fixture
def db():
    url = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    # TEST_DATABASE_URL must refer to a disposable, dedicated test database.
    engine = create_engine(
        url,
        **(
            {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
            if url == "sqlite://"
            else {}
        ),
    )
    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as session:
        seed(session)
        session.commit()
        yield session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def client(db):
    def override():
        yield db

    app.dependency_overrides[get_db] = override
    limiter.clear()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def headers(client):
    def make(tenant="northstar", username="pilot"):
        response = client.post(
            "/auth/login",
            json={
                "username": username,
                "password": os.environ["DEMO_PASSWORD"],
                "tenant_id": tenant,
            },
        )
        assert response.status_code == 200, response.text
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    return make
