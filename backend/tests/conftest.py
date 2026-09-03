import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.main import app
from app.models import User
from app.models.enums import UserRole
from app.services.auth import create_access_token, hash_password


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def unauthenticated_client(session):
    """TestClient wired to the in-memory `session` fixture instead of the
    app's real file-based DB. Not entered as a `with` block, so FastAPI's
    startup lifespan (which calls init_db() against the real DB) never
    runs — irrelevant here since get_session is overridden anyway."""

    def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_token(session):
    """Creates a user with the given role and returns a valid bearer token
    for it — used by RBAC tests that need to act as a specific role."""

    def _make_token(role: UserRole, email: str = "test-user@acme.test") -> str:
        user = User(email=email, hashed_password=hash_password("irrelevant"), role=role)
        session.add(user)
        session.commit()
        session.refresh(user)
        return create_access_token(user)

    return _make_token


@pytest.fixture
def client(unauthenticated_client, make_token):
    """Pre-authenticated as hr_manager by default, since that role has full
    read/write on Employee/SalaryRecord and read access to analytics too -
    covering every existing CRUD/analytics test without each one needing to
    attach its own token. Tests that care about a specific role pass their
    own Authorization header (via make_token) to override this default."""
    token = make_token(UserRole.hr_manager, email="default-hr@acme.test")
    unauthenticated_client.headers["Authorization"] = f"Bearer {token}"
    return unauthenticated_client