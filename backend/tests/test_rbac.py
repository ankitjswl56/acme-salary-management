"""Cross-role access tests. The individual CRUD/analytics endpoints already
have their own behavioral tests (using the default hr_manager-authenticated
`client` fixture) — this file only covers the RBAC boundary itself: who can
and can't reach a given endpoint."""

from app.models.enums import UserRole


def _employee_payload(**overrides):
    payload = {
        "name": "Ada Lovelace",
        "email": "ada@acme.test",
        "country": "UK",
        "department": "Engineering",
        "role": "Senior Software Engineer",
        "hire_date": "2020-01-15",
        "status": "active",
    }
    payload.update(overrides)
    return payload


def test_employees_list_requires_auth(unauthenticated_client):
    response = unauthenticated_client.get("/employees")

    assert response.status_code == 401


def test_employees_create_requires_auth(unauthenticated_client):
    response = unauthenticated_client.post("/employees", json=_employee_payload())

    assert response.status_code == 401


def test_analytics_requires_auth(unauthenticated_client):
    response = unauthenticated_client.get("/analytics/salary-by-country")

    assert response.status_code == 401


def test_health_does_not_require_auth(unauthenticated_client):
    response = unauthenticated_client.get("/health")

    assert response.status_code == 200


def test_invalid_token_is_rejected(unauthenticated_client):
    response = unauthenticated_client.get(
        "/employees", headers={"Authorization": "Bearer not-a-real-token"}
    )

    assert response.status_code == 401


def test_executive_viewer_cannot_list_employees(client, make_token):
    token = make_token(UserRole.executive_viewer, email="exec@acme.test")

    response = client.get("/employees", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_executive_viewer_cannot_create_employee(client, make_token):
    token = make_token(UserRole.executive_viewer, email="exec@acme.test")

    response = client.post(
        "/employees", json=_employee_payload(), headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_executive_viewer_cannot_read_salary_records(client, make_token):
    employee = client.post("/employees", json=_employee_payload()).json()  # as default hr_manager
    token = make_token(UserRole.executive_viewer, email="exec@acme.test")

    response = client.get(
        f"/employees/{employee['id']}/salary-records", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_executive_viewer_can_read_analytics(client, make_token):
    token = make_token(UserRole.executive_viewer, email="exec@acme.test")

    response = client.get("/analytics/salary-by-country", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200


def test_admin_has_full_employee_access(client, make_token):
    token = make_token(UserRole.admin, email="admin@acme.test")

    response = client.post(
        "/employees", json=_employee_payload(), headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 201


def test_hr_manager_can_read_analytics(client):
    """client is hr_manager-authenticated by default."""
    response = client.get("/analytics/salary-by-country")

    assert response.status_code == 200