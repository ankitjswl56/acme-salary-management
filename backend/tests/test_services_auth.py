import time

import jwt
import pytest

from app.config import settings
from app.models import User
from app.models.enums import UserRole
from app.services.auth import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_store_plaintext():
    hashed = hash_password("s3cret!")

    assert hashed != "s3cret!"
    assert verify_password("s3cret!", hashed)


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("s3cret!")

    assert not verify_password("wrong-password", hashed)


def test_create_and_decode_access_token_round_trips():
    user = User(id=1, email="hr@acme.test", hashed_password="irrelevant", role=UserRole.hr_manager)

    token = create_access_token(user)
    payload = decode_access_token(token)

    assert payload.user_id == 1
    assert payload.email == "hr@acme.test"
    assert payload.role == UserRole.hr_manager


def test_decode_access_token_rejects_garbage():
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-real-token")


def test_decode_access_token_rejects_expired_token():
    user = User(id=1, email="hr@acme.test", hashed_password="irrelevant", role=UserRole.hr_manager)
    expired_payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "iat": 0,
        "exp": int(time.time()) - 3600,
    }
    expired_token = jwt.encode(expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    with pytest.raises(InvalidTokenError):
        decode_access_token(expired_token)


def test_decode_access_token_rejects_wrong_signature():
    user = User(id=1, email="hr@acme.test", hashed_password="irrelevant", role=UserRole.hr_manager)
    token = jwt.encode(
        {"sub": str(user.id), "email": user.email, "role": user.role.value},
        "a-different-secret",
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(token)