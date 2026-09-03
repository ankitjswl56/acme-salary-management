"""Light wiring tests only — the actual aggregation logic (median math,
future-dated exclusion, gender-suppression boundary, quarter math, etc.) is
already covered thoroughly in test_services_analytics.py. These just check
each endpoint is mounted, returns 200, and shapes its response correctly."""

from datetime import date

from app.models import ChangeType, Employee, EmployeeStatus, Gender, SalaryRecord


def _seed_one_employee(session, effective_date=date(2020, 1, 1), **overrides):
    defaults = dict(
        name="Ada Lovelace",
        email="ada@acme.test",
        country="UK",
        department="Engineering",
        role="Senior Software Engineer",
        gender=Gender.female,
        hire_date=date(2020, 1, 1),
        status=EmployeeStatus.active,
    )
    defaults.update(overrides)
    employee = Employee(**defaults)
    session.add(employee)
    session.commit()
    session.refresh(employee)

    session.add(
        SalaryRecord(
            employee_id=employee.id,
            amount=90000,
            currency="GBP",
            amount_usd_snapshot=114300,
            fx_rate_to_usd=1.27,
            effective_date=effective_date,
            change_type=ChangeType.hire,
        )
    )
    session.commit()
    return employee


def test_salary_by_country(client, session):
    _seed_one_employee(session)

    response = client.get("/analytics/salary-by-country")

    assert response.status_code == 200
    assert response.json() == [
        {"country": "UK", "headcount": 1, "avg_salary_usd": 114300.0, "median_salary_usd": 114300.0}
    ]


def test_salary_by_department(client, session):
    _seed_one_employee(session)

    response = client.get("/analytics/salary-by-department")

    assert response.status_code == 200
    assert response.json()[0]["department"] == "Engineering"


def test_headcount_payroll_by_country(client, session):
    _seed_one_employee(session)

    response = client.get("/analytics/headcount-payroll-by-country")

    assert response.status_code == 200
    assert response.json() == [{"country": "UK", "headcount": 1, "total_payroll_usd": 114300.0}]


def test_salary_distribution(client, session):
    _seed_one_employee(session)

    response = client.get("/analytics/salary-distribution")

    assert response.status_code == 200
    bands = {row["band"]: row["headcount"] for row in response.json()}
    assert bands["$100k-$125k"] == 1


def test_gender_ratio(client, session):
    _seed_one_employee(session)

    response = client.get("/analytics/gender-ratio")

    assert response.status_code == 200
    assert response.json() == [{"gender": "female", "headcount": 1}]


def test_salary_by_gender_suppresses_small_groups_by_default(client, session):
    _seed_one_employee(session)

    response = client.get("/analytics/salary-by-gender")

    assert response.status_code == 200
    body = response.json()[0]
    assert body["headcount"] == 1
    assert body["suppressed"] is True
    assert body["avg_salary_usd"] is None


def test_salary_by_gender_respects_min_group_size_override(client, session):
    _seed_one_employee(session)

    response = client.get("/analytics/salary-by-gender", params={"min_group_size": 1})

    body = response.json()[0]
    assert body["suppressed"] is False
    assert body["avg_salary_usd"] == 114300.0


def test_recent_changes(client, session):
    _seed_one_employee(session, effective_date=date.today(), hire_date=date.today())

    response = client.get("/analytics/recent-changes")

    assert response.status_code == 200
    assert response.json()[0]["employee_name"] == "Ada Lovelace"


def test_payroll_trend(client, session):
    _seed_one_employee(session)

    response = client.get("/analytics/payroll-trend")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 8
    assert body[-1]["total_payroll_usd"] == 114300.0