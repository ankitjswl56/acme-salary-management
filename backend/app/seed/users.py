"""Demo users — one per role, same shared password, so the reviewer can log
in as each and see the RBAC differences directly (login itself lands in
Phase 5; this just seeds the accounts ahead of it)."""

from app.models.enums import UserRole
from app.services.auth import hash_password

DEMO_PASSWORD = "Password123!@#"

DEMO_USERS = [
    {"email": "admin@acme-corp.example", "role": UserRole.admin},
    {"email": "hr.manager@acme-corp.example", "role": UserRole.hr_manager},
    {"email": "exec.viewer@acme-corp.example", "role": UserRole.executive_viewer},
]


def generate_demo_user_rows() -> list[dict]:
    hashed_password = hash_password(DEMO_PASSWORD)
    return [
        {
            "id": i,
            "email": demo_user["email"],
            "hashed_password": hashed_password,
            "role": demo_user["role"].value,
        }
        for i, demo_user in enumerate(DEMO_USERS, start=1)
    ]