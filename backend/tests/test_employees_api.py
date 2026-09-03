from datetime import date

from app.models import ChangeType, SalaryRecord


def _employee_payload(**overrides):
    payload = {
        "name": "Ada Lovelace",
        "email": "ada@acme.test",
        "country": "UK",
        "department": "Engineering",
        "role": "Senior Software Engineer",
        "gender": "female",
        "hire_date": "2020-01-15",
        "status": "active",
    }
    payload.update(overrides)
    return payload


def test_create_employee_returns_201(client):
    response = client.post("/employees", json=_employee_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["email"] == "ada@acme.test"
    assert body["status"] == "active"


def test_create_employee_rejects_duplicate_email(client):
    client.post("/employees", json=_employee_payload())

    response = client.post("/employees", json=_employee_payload(name="Someone Else"))

    assert response.status_code == 409


def test_get_employee_404_when_missing(client):
    response = client.get("/employees/999")

    assert response.status_code == 404


def test_get_employee_current_salary_is_null_with_no_salary_records(client):
    created = client.post("/employees", json=_employee_payload()).json()

    response = client.get(f"/employees/{created['id']}")

    assert response.status_code == 200
    assert response.json()["current_salary"] is None


def test_get_employee_returns_current_salary_from_latest_past_dated_record(client, session):
    created = client.post("/employees", json=_employee_payload()).json()
    session.add(
        SalaryRecord(
            employee_id=created["id"],
            amount=90000,
            currency="GBP",
            amount_usd_snapshot=114300,
            fx_rate_to_usd=1.27,
            effective_date=date(2020, 1, 15),
            change_type=ChangeType.hire,
        )
    )
    session.add(
        SalaryRecord(
            employee_id=created["id"],
            amount=100000,
            currency="GBP",
            amount_usd_snapshot=127000,
            fx_rate_to_usd=1.27,
            effective_date=date(2100, 1, 1),  # far future - must not be "current"
            change_type=ChangeType.raise_,
        )
    )
    session.commit()

    response = client.get(f"/employees/{created['id']}")

    current_salary = response.json()["current_salary"]
    assert current_salary["amount"] == 90000
    assert current_salary["change_type"] == "hire"


def test_list_employees_filters_by_country_and_paginates(client):
    client.post("/employees", json=_employee_payload(email="a@acme.test", country="UK"))
    client.post("/employees", json=_employee_payload(email="b@acme.test", country="US"))
    client.post("/employees", json=_employee_payload(email="c@acme.test", country="UK"))

    response = client.get("/employees", params={"country": "UK", "limit": 1})

    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 1


def test_update_employee_partial_patch(client):
    created = client.post("/employees", json=_employee_payload()).json()

    response = client.patch(f"/employees/{created['id']}", json={"department": "Product"})

    assert response.status_code == 200
    body = response.json()
    assert body["department"] == "Product"
    assert body["name"] == "Ada Lovelace"  # untouched fields preserved


def test_update_employee_404_when_missing(client):
    response = client.patch("/employees/999", json={"department": "Product"})

    assert response.status_code == 404


def test_get_filter_options_returns_distinct_sorted_values(client):
    client.post("/employees", json=_employee_payload(email="a@acme.test", country="US", department="Sales"))
    client.post("/employees", json=_employee_payload(email="b@acme.test", country="UK", department="Sales"))
    client.post("/employees", json=_employee_payload(email="c@acme.test", country="US", department="Engineering"))

    response = client.get("/employees/filters")

    assert response.status_code == 200
    body = response.json()
    assert body["countries"] == [
        {"code": "UK", "name": "United Kingdom"},
        {"code": "US", "name": "United States"},
    ]
    assert body["departments"] == ["Engineering", "Sales"]


def test_get_filter_options_resolves_unknown_country_code_to_itself(client):
    """A country added by hand through the API (not the seed script) won't
    be in the reference table - falls back to the code as its own label
    rather than erroring."""
    client.post("/employees", json=_employee_payload(country="ZZ"))

    response = client.get("/employees/filters")

    assert response.json()["countries"] == [{"code": "ZZ", "name": "ZZ"}]


def test_get_filter_options_empty_when_no_employees(client):
    response = client.get("/employees/filters")

    assert response.status_code == 200
    assert response.json() == {"countries": [], "departments": []}