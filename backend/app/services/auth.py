"""Password hashing + JWT issuing/verification.

Deliberately minimal per CLAUDE.md: no password reset, email verification,
refresh-token rotation, or SSO. A token just asserts (user_id, email, role)
for jwt_expire_minutes; there's no revocation list, so a role change or
account removal only takes effect once the current token expires or the
user is looked up again (see get_current_user in app/dependencies.py, which
re-fetches the user rather than trusting the token's role blindly).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings
from app.models import User
from app.models.enums import UserRole


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


@dataclass(frozen=True)
class TokenPayload:
    user_id: int
    email: str
    role: UserRole


class InvalidTokenError(Exception):
    pass


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    try:
        return TokenPayload(
            user_id=int(payload["sub"]), email=payload["email"], role=UserRole(payload["role"])
        )
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("Malformed token payload") from exc