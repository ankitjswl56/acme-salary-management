from app.models import User
from app.models.enums import UserRole
from app.services.auth import hash_password


def _seed_user(session, email="hr@acme.test", password="correct-password", role=UserRole.hr_manager):
    user = User(email=email, hashed_password=hash_password(password), role=role)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_login_returns_token_on_valid_credentials(unauthenticated_client, session):
    _seed_user(session, email="hr@acme.test", password="correct-password")

    response = unauthenticated_client.post(
        "/auth/login", json={"email": "hr@acme.test", "password": "correct-password"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["role"] == "hr_manager"


def test_login_rejects_wrong_password(unauthenticated_client, session):
    _seed_user(session, email="hr@acme.test", password="correct-password")

    response = unauthenticated_client.post(
        "/auth/login", json={"email": "hr@acme.test", "password": "wrong-password"}
    )

    assert response.status_code == 401


def test_login_rejects_unknown_email(unauthenticated_client, session):
    response = unauthenticated_client.post(
        "/auth/login", json={"email": "nobody@acme.test", "password": "whatever"}
    )

    assert response.status_code == 401