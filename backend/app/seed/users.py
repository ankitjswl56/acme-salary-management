"""Demo users — one per role, same shared password, so the reviewer can log
in as each and see the RBAC differences directly (login itself lands in
Phase 5; this just seeds the accounts ahead of it)."""

import bcrypt

from app.models.enums import UserRole

DEMO_PASSWORD = "Password123!@#"

DEMO_USERS = [
    {"email": "admin@acme-corp.example", "role": UserRole.admin},
    {"email": "hr.manager@acme-corp.example", "role": UserRole.hr_manager},
    {"email": "exec.viewer@acme-corp.example", "role": UserRole.executive_viewer},
]


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def generate_demo_user_rows() -> list[dict]:
    hashed_password = _hash_password(DEMO_PASSWORD)
    return [
        {
            "id": i,
            "email": demo_user["email"],
            "hashed_password": hashed_password,
            "role": demo_user["role"].value,
        }
        for i, demo_user in enumerate(DEMO_USERS, start=1)
    ]