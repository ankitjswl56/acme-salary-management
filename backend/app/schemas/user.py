from pydantic import Field
from sqlmodel import SQLModel

from app.models.enums import UserRole


class UserCreate(SQLModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole


class UserRead(SQLModel):
    """A user, minus the password hash — nothing here exposes credentials."""

    id: int
    email: str
    role: UserRole


class UserRoleUpdate(SQLModel):
    role: UserRole