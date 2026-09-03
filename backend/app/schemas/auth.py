from sqlmodel import SQLModel

from app.models.enums import UserRole


class LoginRequest(SQLModel):
    email: str
    password: str


class LoginResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    role: UserRole