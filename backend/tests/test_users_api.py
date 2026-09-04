"""User-management endpoints — the admin-only slice of RBAC.

The point of this file is the boundary: hr_manager has full data access but
*no* user management, so every route here must 403 for anyone but admin.
Plus the self-lockout guards on role-change and delete.
"""

from sqlmodel import select

from app.models import User
from app.models.enums import UserRole
from app.services.auth import verify_password


def _admin_headers(make_token) -> dict:
    return {"Authorization": f"Bearer {make_token(UserRole.admin, email='admin@acme.test')}"}


# --- RBAC boundary --------------------------------------------------------


def test_listing_users_requires_auth(unauthenticated_client):
    assert unauthenticated_client.get("/users").status_code == 401


def test_hr_manager_cannot_touch_user_management(client, make_token):
    token = make_token(UserRole.hr_manager, email="hr2@acme.test")
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/users", headers=headers).status_code == 403
    assert client.post(
        "/users",
        json={"email": "x@acme.test", "password": "password123", "role": "hr_manager"},
        headers=headers,
    ).status_code == 403
    assert client.patch("/users/1", json={"role": "admin"}, headers=headers).status_code == 403
    assert client.delete("/users/1", headers=headers).status_code == 403


def test_executive_viewer_cannot_list_users(client, make_token):
    token = make_token(UserRole.executive_viewer, email="exec@acme.test")
    assert client.get("/users", headers={"Authorization": f"Bearer {token}"}).status_code == 403


# --- list / create ------------------------------------------------------


def test_admin_can_list_users(client, make_token):
    headers = _admin_headers(make_token)
    response = client.get("/users", headers=headers)

    assert response.status_code == 200
    emails = [u["email"] for u in response.json()]
    assert "admin@acme.test" in emails
    # never leak the hash
    assert all("password" not in u and "hashed_password" not in u for u in response.json())


def test_admin_creates_a_user_and_the_password_is_hashed(client, make_token, session):
    headers = _admin_headers(make_token)
    response = client.post(
        "/users",
        json={"email": "new.hr@acme.test", "password": "s3cretpassword", "role": "hr_manager"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new.hr@acme.test"
    assert body["role"] == "hr_manager"
    assert "id" in body and "password" not in body and "hashed_password" not in body

    stored = session.exec(select(User).where(User.email == "new.hr@acme.test")).one()
    assert stored.hashed_password != "s3cretpassword"
    assert verify_password("s3cretpassword", stored.hashed_password)


def test_create_rejects_a_duplicate_email(client, make_token):
    headers = _admin_headers(make_token)
    payload = {"email": "dupe@acme.test", "password": "password123", "role": "hr_manager"}

    assert client.post("/users", json=payload, headers=headers).status_code == 201
    assert client.post("/users", json=payload, headers=headers).status_code == 409


def test_create_validates_role_and_password_length(client, make_token):
    headers = _admin_headers(make_token)

    assert client.post(
        "/users",
        json={"email": "a@acme.test", "password": "password123", "role": "superuser"},
        headers=headers,
    ).status_code == 422
    assert client.post(
        "/users",
        json={"email": "b@acme.test", "password": "short", "role": "hr_manager"},
        headers=headers,
    ).status_code == 422
    assert client.post("/users", json={"email": "c@acme.test"}, headers=headers).status_code == 422


# --- change role ------------------------------------------------------


def test_admin_can_change_another_users_role(client, make_token):
    headers = _admin_headers(make_token)
    created = client.post(
        "/users",
        json={"email": "promote.me@acme.test", "password": "password123", "role": "executive_viewer"},
        headers=headers,
    ).json()

    response = client.patch(f"/users/{created['id']}", json={"role": "hr_manager"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["role"] == "hr_manager"

    listed = {u["id"]: u for u in client.get("/users", headers=headers).json()}
    assert listed[created["id"]]["role"] == "hr_manager"


def test_admin_cannot_demote_their_own_account(client, make_token):
    headers = _admin_headers(make_token)
    me = next(u for u in client.get("/users", headers=headers).json() if u["email"] == "admin@acme.test")

    response = client.patch(f"/users/{me['id']}", json={"role": "hr_manager"}, headers=headers)
    assert response.status_code == 400
    # still admin
    still = next(
        u for u in client.get("/users", headers=headers).json() if u["id"] == me["id"]
    )
    assert still["role"] == "admin"


def test_patching_a_missing_user_is_404(client, make_token):
    headers = _admin_headers(make_token)
    assert client.patch("/users/99999", json={"role": "admin"}, headers=headers).status_code == 404


# --- delete ----------------------------------------------------------


def test_admin_can_delete_another_user(client, make_token):
    headers = _admin_headers(make_token)
    created = client.post(
        "/users",
        json={"email": "delete.me@acme.test", "password": "password123", "role": "hr_manager"},
        headers=headers,
    ).json()

    assert client.delete(f"/users/{created['id']}", headers=headers).status_code == 204
    remaining = [u["id"] for u in client.get("/users", headers=headers).json()]
    assert created["id"] not in remaining


def test_admin_cannot_delete_their_own_account(client, make_token):
    headers = _admin_headers(make_token)
    me = next(u for u in client.get("/users", headers=headers).json() if u["email"] == "admin@acme.test")

    assert client.delete(f"/users/{me['id']}", headers=headers).status_code == 400
    assert client.get("/users", headers=headers).status_code == 200  # still authorised


def test_deleting_a_missing_user_is_404(client, make_token):
    headers = _admin_headers(make_token)
    assert client.delete("/users/99999", headers=headers).status_code == 404