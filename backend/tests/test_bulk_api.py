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


def test_bulk_raise_applies_and_reports_counts(client):
    employee = client.post("/employees", json=_employee_payload()).json()
    client.post(
        f"/employees/{employee['id']}/salary-records",
        json={"amount": 90000, "currency": "GBP", "effective_date": "2020-01-15", "change_type": "hire"},
    )

    response = client.post(
        "/employees/bulk-raise", json={"percentage": 10, "effective_date": "2026-01-01"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["matched_count"] == 1
    assert body["applied_count"] == 1

    updated = client.get(f"/employees/{employee['id']}").json()
    assert updated["current_salary"]["amount"] == 99000.0


def test_bulk_raise_ignores_a_status_field_sneaked_into_the_request(client):
    """There's no status parameter on BulkRaiseRequest - confirms an extra
    "status" key in the request body can't sneak an inactive employee into
    scope; it's just ignored, and only active employees are ever matched."""
    active = client.post("/employees", json=_employee_payload(email="active@acme.test")).json()
    inactive = client.post(
        "/employees", json=_employee_payload(email="inactive@acme.test", status="inactive")
    ).json()
    for employee in (active, inactive):
        client.post(
            f"/employees/{employee['id']}/salary-records",
            json={"amount": 90000, "currency": "USD", "effective_date": "2020-01-15", "change_type": "hire"},
        )

    response = client.post(
        "/employees/bulk-raise",
        json={"percentage": 10, "effective_date": "2026-01-01", "status": "inactive"},
    )

    assert response.status_code == 200
    assert response.json()["matched_count"] == 1  # only the active employee, "status" was ignored


def test_bulk_raise_400_for_disallowed_change_type(client):
    response = client.post(
        "/employees/bulk-raise",
        json={"percentage": 10, "effective_date": "2026-01-01", "change_type": "correction"},
    )

    assert response.status_code == 400


def test_bulk_raise_requires_admin_or_hr_manager(client, make_token):
    token = make_token(UserRole.executive_viewer, email="exec@acme.test")

    response = client.post(
        "/employees/bulk-raise",
        json={"percentage": 10, "effective_date": "2026-01-01"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403