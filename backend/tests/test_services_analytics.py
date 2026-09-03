from datetime import date

from app.models import ChangeType, Employee, EmployeeStatus, Gender, SalaryRecord
from app.services.analytics import (
    avg_median_salary_by_country,
    avg_median_salary_by_department,
    get_current_salary_snapshots,
    headcount_and_payroll_by_country,
)

TODAY = date(2026, 9, 2)


def _make_employee(
    session,
    *,
    email: str,
    country: str = "US",
    department: str = "Engineering",
    gender: Gender | None = Gender.female,
    status: EmployeeStatus = EmployeeStatus.active,
    hire_date: date = date(2020, 1, 1),
) -> Employee:
    employee = Employee(
        name=email.split("@")[0],
        email=email,
        country=country,
        department=department,
        role="Engineer",
        gender=gender,
        hire_date=hire_date,
        status=status,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def _add_record(session, employee: Employee, amount_usd: float, effective_date: date, change_type=ChangeType.hire):
    record = SalaryRecord(
        employee_id=employee.id,
        amount=amount_usd,
        currency="USD",
        amount_usd_snapshot=amount_usd,
        fx_rate_to_usd=1.0,
        effective_date=effective_date,
        change_type=change_type,
    )
    session.add(record)
    session.commit()


def test_snapshots_exclude_future_dated_records(session):
    employee = _make_employee(session, email="a@acme.test")
    _add_record(session, employee, 90000, date(2020, 1, 1), ChangeType.hire)
    _add_record(session, employee, 999999, date(2100, 1, 1), ChangeType.raise_)  # far future

    snapshots = get_current_salary_snapshots(session, as_of=TODAY)

    assert len(snapshots) == 1
    assert snapshots[0].amount_usd == 90000


def test_snapshots_exclude_employees_with_no_applicable_record(session):
    employee = _make_employee(session, email="a@acme.test")
    _add_record(session, employee, 90000, date(2100, 1, 1), ChangeType.hire)  # only a future record

    snapshots = get_current_salary_snapshots(session, as_of=TODAY)

    assert snapshots == []


def test_snapshots_active_only_excludes_inactive_employees_by_default(session):
    active = _make_employee(session, email="active@acme.test", status=EmployeeStatus.active)
    inactive = _make_employee(session, email="inactive@acme.test", status=EmployeeStatus.inactive)
    _add_record(session, active, 90000, date(2020, 1, 1))
    _add_record(session, inactive, 80000, date(2020, 1, 1))

    active_only = get_current_salary_snapshots(session, as_of=TODAY, active_only=True)
    everyone = get_current_salary_snapshots(session, as_of=TODAY, active_only=False)

    assert [s.employee_id for s in active_only] == [active.id]
    assert {s.employee_id for s in everyone} == {active.id, inactive.id}


def test_avg_median_salary_by_country_computes_correct_stats(session):
    for email, amount in [("a@acme.test", 50000), ("b@acme.test", 60000), ("c@acme.test", 100000)]:
        employee = _make_employee(session, email=email, country="US")
        _add_record(session, employee, amount, date(2020, 1, 1))

    result = avg_median_salary_by_country(session, as_of=TODAY)

    assert result == [
        {"country": "US", "headcount": 3, "avg_salary_usd": 70000.0, "median_salary_usd": 60000.0}
    ]


def test_avg_median_salary_by_country_groups_countries_separately(session):
    us_employee = _make_employee(session, email="us@acme.test", country="US")
    in_employee = _make_employee(session, email="in@acme.test", country="IN")
    _add_record(session, us_employee, 100000, date(2020, 1, 1))
    _add_record(session, in_employee, 30000, date(2020, 1, 1))

    result = avg_median_salary_by_country(session, as_of=TODAY)

    by_country = {row["country"]: row for row in result}
    assert by_country["US"]["avg_salary_usd"] == 100000.0
    assert by_country["IN"]["avg_salary_usd"] == 30000.0


def test_avg_median_salary_by_department_groups_correctly(session):
    eng = _make_employee(session, email="eng@acme.test", department="Engineering")
    support = _make_employee(session, email="support@acme.test", department="Support")
    _add_record(session, eng, 120000, date(2020, 1, 1))
    _add_record(session, support, 50000, date(2020, 1, 1))

    result = avg_median_salary_by_department(session, as_of=TODAY)

    by_dept = {row["department"]: row for row in result}
    assert by_dept["Engineering"]["avg_salary_usd"] == 120000.0
    assert by_dept["Support"]["avg_salary_usd"] == 50000.0


def test_headcount_and_payroll_by_country_sums_current_salaries(session):
    for email, amount in [("a@acme.test", 50000), ("b@acme.test", 70000)]:
        employee = _make_employee(session, email=email, country="UK")
        _add_record(session, employee, amount, date(2020, 1, 1))

    result = headcount_and_payroll_by_country(session, as_of=TODAY)

    assert result == [{"country": "UK", "headcount": 2, "total_payroll_usd": 120000.0}]