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


def _create_employee(client, **overrides):
    return client.post("/employees", json=_employee_payload(**overrides)).json()


def test_add_salary_record_returns_201_with_usd_normalization(client):
    employee = _create_employee(client)

    response = client.post(
        f"/employees/{employee['id']}/salary-records",
        json={"amount": 90000, "currency": "GBP", "effective_date": "2020-01-15", "change_type": "hire"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["employee_id"] == employee["id"]
    assert body["fx_rate_to_usd"] == 1.27
    assert body["amount_usd_snapshot"] == 114300.0


def test_add_salary_record_404_when_employee_missing(client):
    response = client.post(
        "/employees/999/salary-records",
        json={"amount": 90000, "currency": "GBP", "effective_date": "2020-01-15", "change_type": "hire"},
    )

    assert response.status_code == 404


def test_add_salary_record_400_for_unsupported_currency(client):
    employee = _create_employee(client)

    response = client.post(
        f"/employees/{employee['id']}/salary-records",
        json={"amount": 90000, "currency": "ZZZ", "effective_date": "2020-01-15", "change_type": "hire"},
    )

    assert response.status_code == 400


def test_add_salary_record_400_for_effective_date_before_hire(client):
    employee = _create_employee(client)  # hired 2020-01-15

    response = client.post(
        f"/employees/{employee['id']}/salary-records",
        json={"amount": 90000, "currency": "GBP", "effective_date": "2019-01-01", "change_type": "hire"},
    )

    assert response.status_code == 400


def test_list_salary_records_returns_history_newest_first(client):
    employee = _create_employee(client)
    client.post(
        f"/employees/{employee['id']}/salary-records",
        json={"amount": 90000, "currency": "GBP", "effective_date": "2020-01-15", "change_type": "hire"},
    )
    client.post(
        f"/employees/{employee['id']}/salary-records",
        json={"amount": 100000, "currency": "GBP", "effective_date": "2022-06-01", "change_type": "raise"},
    )

    response = client.get(f"/employees/{employee['id']}/salary-records")

    body = response.json()
    assert len(body) == 2
    assert body[0]["change_type"] == "raise"
    assert body[1]["change_type"] == "hire"


def test_list_salary_records_404_when_employee_missing(client):
    response = client.get("/employees/999/salary-records")

    assert response.status_code == 404