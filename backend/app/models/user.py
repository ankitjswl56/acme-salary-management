from typing import Optional

from sqlmodel import Field, SQLModel

from app.models.enums import UserRole, enum_column


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    hashed_password: str
    role: UserRole = Field(sa_column=enum_column(UserRole, nullable=False))
