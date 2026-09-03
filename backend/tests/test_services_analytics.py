from datetime import date

from app.models import ChangeType, Employee, EmployeeStatus, Gender, SalaryRecord
from app.services.analytics import (
    avg_median_salary_by_country,
    avg_median_salary_by_department,
    avg_salary_by_gender,
    gender_ratio,
    get_current_salary_snapshots,
    headcount_and_payroll_by_country,
    salary_distribution,
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


def test_salary_distribution_buckets_by_fixed_bands_including_empty_ones(session):
    for email, amount in [("a@acme.test", 20000), ("b@acme.test", 60000), ("c@acme.test", 65000)]:
        employee = _make_employee(session, email=email)
        _add_record(session, employee, amount, date(2020, 1, 1))

    result = salary_distribution(session, as_of=TODAY)

    by_band = {row["band"]: row["headcount"] for row in result}
    assert by_band["<$30k"] == 1
    assert by_band["$50k-$75k"] == 2
    assert by_band["$75k-$100k"] == 0  # empty band still present
    assert sum(by_band.values()) == 3


def test_gender_ratio_counts_active_employees_by_gender(session):
    _make_employee(session, email="a@acme.test", gender=Gender.female)
    _make_employee(session, email="b@acme.test", gender=Gender.female)
    _make_employee(session, email="c@acme.test", gender=Gender.male)
    _make_employee(session, email="d@acme.test", gender=None)
    _make_employee(session, email="e@acme.test", gender=Gender.male, status=EmployeeStatus.inactive)

    result = gender_ratio(session)

    by_gender = {row["gender"]: row["headcount"] for row in result}
    assert by_gender["female"] == 2
    assert by_gender["male"] == 1  # inactive employee excluded by default
    assert by_gender["unspecified"] == 1


def test_gender_ratio_filters_by_department(session):
    _make_employee(session, email="a@acme.test", department="Engineering", gender=Gender.female)
    _make_employee(session, email="b@acme.test", department="Sales", gender=Gender.female)

    result = gender_ratio(session, department="Engineering")

    assert result == [{"gender": "female", "headcount": 1}]


def test_avg_salary_by_gender_suppressed_below_min_group_size(session):
    for i in range(4):  # one below the default threshold of 5
        employee = _make_employee(session, email=f"f{i}@acme.test", gender=Gender.female)
        _add_record(session, employee, 100000, date(2020, 1, 1))

    result = avg_salary_by_gender(session, as_of=TODAY)

    female_row = next(row for row in result if row["gender"] == "female")
    assert female_row["headcount"] == 4
    assert female_row["suppressed"] is True
    assert female_row["avg_salary_usd"] is None


def test_avg_salary_by_gender_shown_at_exactly_min_group_size(session):
    for i in range(5):  # exactly at the default threshold
        employee = _make_employee(session, email=f"f{i}@acme.test", gender=Gender.female)
        _add_record(session, employee, 100000, date(2020, 1, 1))

    result = avg_salary_by_gender(session, as_of=TODAY)

    female_row = next(row for row in result if row["gender"] == "female")
    assert female_row["headcount"] == 5
    assert female_row["suppressed"] is False
    assert female_row["avg_salary_usd"] == 100000.0


def test_avg_salary_by_gender_respects_custom_min_group_size(session):
    for i in range(5):
        employee = _make_employee(session, email=f"f{i}@acme.test", gender=Gender.female)
        _add_record(session, employee, 100000, date(2020, 1, 1))

    result = avg_salary_by_gender(session, as_of=TODAY, min_group_size=10)

    female_row = next(row for row in result if row["gender"] == "female")
    assert female_row["suppressed"] is True
    assert female_row["avg_salary_usd"] is None


def test_avg_salary_by_gender_filters_by_department_and_role(session):
    eng = _make_employee(session, email="eng@acme.test", department="Engineering", gender=Gender.female)
    sales = _make_employee(session, email="sales@acme.test", department="Sales", gender=Gender.female)
    _add_record(session, eng, 120000, date(2020, 1, 1))
    _add_record(session, sales, 60000, date(2020, 1, 1))

    result = avg_salary_by_gender(session, department="Engineering", as_of=TODAY, min_group_size=1)

    assert result == [{"gender": "female", "headcount": 1, "avg_salary_usd": 120000.0, "suppressed": False}]