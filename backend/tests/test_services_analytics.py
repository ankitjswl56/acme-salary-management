from datetime import date

from app.models import ChangeType, Employee, EmployeeStatus, Gender, SalaryRecord
from app.services import analytics as analytics_service
from app.services.analytics import (
    _quarter_end_dates,
    avg_median_salary_by_country,
    avg_median_salary_by_department,
    avg_salary_by_gender,
    dashboard_summary,
    gender_ratio,
    get_current_salary_snapshots,
    headcount_and_payroll_by_country,
    payroll_trend_by_quarter,
    recent_changes_feed,
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


def test_recent_changes_feed_includes_only_records_within_the_window(session):
    employee = _make_employee(session, email="a@acme.test", hire_date=date(2020, 1, 1))
    _add_record(session, employee, 90000, date(2020, 1, 1), ChangeType.hire)
    _add_record(session, employee, 95000, date(2026, 7, 1), ChangeType.raise_)  # within last 3 months
    _add_record(session, employee, 100000, date(2026, 12, 1), ChangeType.raise_)  # future, beyond as_of

    result = recent_changes_feed(session, months=3, as_of=TODAY)

    effective_dates = {row["effective_date"] for row in result}
    assert date(2026, 7, 1) in effective_dates
    assert date(2020, 1, 1) not in effective_dates  # too old
    assert date(2026, 12, 1) not in effective_dates  # future relative to as_of


def test_recent_changes_feed_filters_by_change_type(session):
    employee = _make_employee(session, email="a@acme.test", hire_date=date(2020, 1, 1))
    _add_record(session, employee, 90000, date(2026, 7, 1), ChangeType.raise_)
    _add_record(session, employee, 95000, date(2026, 7, 15), ChangeType.promotion)

    result = recent_changes_feed(session, months=3, as_of=TODAY, change_type=ChangeType.promotion)

    assert len(result) == 1
    assert result[0]["change_type"] == "promotion"


def test_recent_changes_feed_orders_newest_first(session):
    employee = _make_employee(session, email="a@acme.test", hire_date=date(2020, 1, 1))
    _add_record(session, employee, 90000, date(2026, 6, 15), ChangeType.raise_)
    _add_record(session, employee, 95000, date(2026, 8, 1), ChangeType.raise_)

    result = recent_changes_feed(session, months=3, as_of=TODAY)

    assert [row["effective_date"] for row in result] == [date(2026, 8, 1), date(2026, 6, 15)]


def test_recent_changes_feed_respects_limit(session):
    employee = _make_employee(session, email="a@acme.test", hire_date=date(2020, 1, 1))
    for day in range(1, 6):
        _add_record(session, employee, 90000 + day, date(2026, 8, day), ChangeType.raise_)

    result = recent_changes_feed(session, months=3, as_of=TODAY, limit=2)

    assert len(result) == 2


def test_payroll_trend_by_quarter_reflects_salary_at_each_past_quarter_end(session):
    employee = _make_employee(session, email="a@acme.test", hire_date=date(2020, 1, 1))
    _add_record(session, employee, 80000, date(2020, 1, 1), ChangeType.hire)
    _add_record(session, employee, 100000, date(2026, 5, 1), ChangeType.raise_)  # effective in Q2 2026

    result = payroll_trend_by_quarter(session, quarters=4, as_of=TODAY)  # Q4'25..Q3'26
    by_quarter = {row["quarter"]: row for row in result}

    assert by_quarter["2026-Q1"]["total_payroll_usd"] == 80000.0
    assert by_quarter["2026-Q2"]["total_payroll_usd"] == 100000.0
    assert by_quarter["2026-Q3"]["total_payroll_usd"] == 100000.0


def test_payroll_trend_by_quarter_current_quarter_caps_at_as_of(session):
    """A raise already scheduled later this quarter must not inflate the
    current quarter's payroll before it actually takes effect."""
    employee = _make_employee(session, email="a@acme.test", hire_date=date(2020, 1, 1))
    _add_record(session, employee, 100000, date(2020, 1, 1), ChangeType.hire)
    _add_record(session, employee, 150000, date(2026, 9, 15), ChangeType.raise_)  # after TODAY, same quarter

    result = payroll_trend_by_quarter(session, quarters=1, as_of=TODAY)

    assert result == [{"quarter": "2026-Q3", "headcount": 1, "total_payroll_usd": 100000.0}]


def test_payroll_trend_by_quarter_includes_currently_inactive_employees(session):
    """Historical payroll trend isn't filtered by *current* status - there's
    no tracked termination date, so status can't tell us who was active in a
    past quarter."""
    employee = _make_employee(
        session, email="a@acme.test", hire_date=date(2020, 1, 1), status=EmployeeStatus.inactive
    )
    _add_record(session, employee, 90000, date(2020, 1, 1), ChangeType.hire)

    result = payroll_trend_by_quarter(session, quarters=1, as_of=TODAY)

    assert result == [{"quarter": "2026-Q3", "headcount": 1, "total_payroll_usd": 90000.0}]


def test_payroll_trend_by_quarter_returns_requested_count_oldest_first(session):
    result = payroll_trend_by_quarter(session, quarters=3, as_of=TODAY)

    assert [row["quarter"] for row in result] == ["2026-Q1", "2026-Q2", "2026-Q3"]


def test_payroll_trend_matches_per_quarter_snapshot_resolution(session):
    """The single-fetch rewrite must produce exactly what resolving the
    current salary per quarter-end via get_current_salary_snapshots would."""
    # hire-only, well before the window
    e1 = _make_employee(session, email="e1@acme.test", hire_date=date(2020, 1, 1))
    _add_record(session, e1, 90000, date(2020, 1, 1), ChangeType.hire)
    # hire + raise straddling a quarter boundary
    e2 = _make_employee(session, email="e2@acme.test", hire_date=date(2024, 1, 1))
    _add_record(session, e2, 100000, date(2024, 1, 1), ChangeType.hire)
    _add_record(session, e2, 120000, date(2025, 5, 10), ChangeType.raise_)
    # currently inactive - still counts historically
    e3 = _make_employee(
        session, email="e3@acme.test", hire_date=date(2023, 6, 1), status=EmployeeStatus.inactive
    )
    _add_record(session, e3, 70000, date(2023, 6, 1), ChangeType.hire)
    # future-dated record - must never enter any quarter
    e4 = _make_employee(session, email="e4@acme.test", hire_date=date(2020, 1, 1))
    _add_record(session, e4, 80000, date(2020, 1, 1), ChangeType.hire)
    _add_record(session, e4, 200000, date(2100, 1, 1), ChangeType.raise_)

    reference = []
    for label, quarter_end in _quarter_end_dates(TODAY, 6):
        snaps = get_current_salary_snapshots(
            session, as_of=min(quarter_end, TODAY), active_only=False
        )
        reference.append(
            {
                "quarter": label,
                "headcount": len(snaps),
                "total_payroll_usd": round(sum(s.amount_usd for s in snaps), 2),
            }
        )

    assert payroll_trend_by_quarter(session, quarters=6, as_of=TODAY) == reference


def test_snapshot_views_accept_a_shared_precomputed_list(session):
    """dashboard_summary computes the snapshot list once and threads it into
    every current-state view; passing snapshots= must match computing it
    per-view."""
    for email, country, dept, gender in [
        ("a@acme.test", "US", "Engineering", Gender.female),
        ("b@acme.test", "US", "Engineering", Gender.male),
        ("c@acme.test", "UK", "Sales", Gender.female),
        ("d@acme.test", "UK", "Sales", Gender.male),
        ("e@acme.test", "UK", "Sales", Gender.female),
    ]:
        employee = _make_employee(session, email=email, country=country, department=dept, gender=gender)
        _add_record(session, employee, 90000, date(2020, 1, 1))

    shared = get_current_salary_snapshots(session, as_of=TODAY)

    assert avg_median_salary_by_country(session, snapshots=shared) == avg_median_salary_by_country(
        session, as_of=TODAY
    )
    assert avg_median_salary_by_department(session, snapshots=shared) == avg_median_salary_by_department(
        session, as_of=TODAY
    )
    assert headcount_and_payroll_by_country(session, snapshots=shared) == headcount_and_payroll_by_country(
        session, as_of=TODAY
    )
    assert salary_distribution(session, snapshots=shared) == salary_distribution(session, as_of=TODAY)
    assert avg_salary_by_gender(session, snapshots=shared) == avg_salary_by_gender(session, as_of=TODAY)
    # department narrowing still applies to the passed list
    assert avg_salary_by_gender(session, department="Sales", snapshots=shared) == avg_salary_by_gender(
        session, department="Sales", as_of=TODAY
    )


def _seed_mixed_dataset(session):
    for email, country, dept, gender, status in [
        ("a@acme.test", "US", "Engineering", Gender.female, EmployeeStatus.active),
        ("b@acme.test", "US", "Engineering", Gender.male, EmployeeStatus.active),
        ("c@acme.test", "UK", "Sales", Gender.female, EmployeeStatus.active),
        ("d@acme.test", "UK", "Sales", Gender.male, EmployeeStatus.inactive),
    ]:
        employee = _make_employee(
            session, email=email, country=country, department=dept, gender=gender, status=status
        )
        _add_record(session, employee, 95000, date(2024, 1, 1), ChangeType.hire)
        if email == "a@acme.test":
            _add_record(session, employee, 110000, date(2025, 6, 1), ChangeType.raise_)


def test_dashboard_summary_matches_the_individual_views(session):
    _seed_mixed_dataset(session)

    d = dashboard_summary(session, as_of=TODAY)

    assert d["as_of"] == TODAY
    assert d["salary_by_country"] == avg_median_salary_by_country(session, as_of=TODAY)
    assert d["salary_by_department"] == avg_median_salary_by_department(session, as_of=TODAY)
    assert d["headcount_payroll_by_country"] == headcount_and_payroll_by_country(session, as_of=TODAY)
    assert d["salary_distribution"] == salary_distribution(session, as_of=TODAY)
    assert d["salary_by_gender"] == avg_salary_by_gender(session, as_of=TODAY)
    assert d["gender_ratio"] == gender_ratio(session)
    assert d["recent_changes"] == recent_changes_feed(session, months=3, as_of=TODAY)
    assert d["payroll_trend"] == payroll_trend_by_quarter(session, quarters=8, as_of=TODAY)


def test_dashboard_summary_computes_snapshots_once(session, monkeypatch):
    _seed_mixed_dataset(session)

    calls = []
    real = analytics_service.get_current_salary_snapshots
    monkeypatch.setattr(
        analytics_service,
        "get_current_salary_snapshots",
        lambda *a, **k: calls.append(1) or real(*a, **k),
    )

    dashboard_summary(session, as_of=TODAY)

    assert len(calls) == 1