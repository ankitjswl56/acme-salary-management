"""User administration — the admin-only slice of RBAC (CLAUDE.md § RBAC:
"admin ... plus user management").

Scoped to what the locked User schema supports: list, create, change role,
delete. There is no `is_active` column, so "deactivate" isn't offered —
removing a user is the way to revoke access. Deliberately no password reset
/ email verification (out of scope per CLAUDE.md).
"""

from sqlmodel import Session, select

from app.models import User
from app.models.enums import UserRole
from app.schemas.user import UserCreate
from app.services.auth import hash_password


class EmailAlreadyExistsError(Exception):
    """A user with the requested email already exists."""


def list_users(session: Session) -> list[User]:
    return list(session.exec(select(User).order_by(User.id)).all())


def create_user(session: Session, data: UserCreate) -> User:
    if session.exec(select(User).where(User.email == data.email)).first() is not None:
        raise EmailAlreadyExistsError(data.email)
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def set_user_role(session: Session, user_id: int, role: UserRole) -> User | None:
    user = session.get(User, user_id)
    if user is None:
        return None
    user.role = role
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def delete_user(session: Session, user_id: int) -> bool:
    user = session.get(User, user_id)
    if user is None:
        return False
    session.delete(user)
    session.commit()
    return True