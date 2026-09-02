from datetime import date

from app.models import ChangeType, Employee, EmployeeStatus, SalaryRecord
from app.services.salary import get_current_salary_record, get_salary_history

TODAY = date(2026, 9, 2)


def _make_employee(session) -> Employee:
    employee = Employee(
        name="Grace Hopper",
        email="grace@acme.test",
        country="US",
        department="Engineering",
        role="Senior Software Engineer",
        hire_date=date(2020, 1, 1),
        status=EmployeeStatus.active,
    )
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def _add_record(session, employee: Employee, amount: float, effective_date: date, change_type=ChangeType.raise_):
    record = SalaryRecord(
        employee_id=employee.id,
        amount=amount,
        currency="USD",
        amount_usd_snapshot=amount,
        fx_rate_to_usd=1.0,
        effective_date=effective_date,
        change_type=change_type,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def test_current_salary_is_none_when_employee_has_no_records(session):
    employee = _make_employee(session)

    assert get_current_salary_record(session, employee.id, as_of=TODAY) is None


def test_current_salary_is_the_single_hire_record(session):
    employee = _make_employee(session)
    hire = _add_record(session, employee, 90000, date(2020, 1, 1), ChangeType.hire)

    current = get_current_salary_record(session, employee.id, as_of=TODAY)

    assert current.id == hire.id
    assert current.amount == 90000


def test_current_salary_is_the_latest_past_dated_record(session):
    employee = _make_employee(session)
    _add_record(session, employee, 90000, date(2020, 1, 1), ChangeType.hire)
    _add_record(session, employee, 100000, date(2021, 6, 1), ChangeType.raise_)
    latest = _add_record(session, employee, 115000, date(2023, 3, 1), ChangeType.promotion)

    current = get_current_salary_record(session, employee.id, as_of=TODAY)

    assert current.id == latest.id
    assert current.amount == 115000


def test_future_dated_record_is_excluded_from_current_salary(session):
    """The core correctness rule: a raise scheduled for next quarter must not
    be treated as current until its effective_date actually arrives."""
    employee = _make_employee(session)
    past = _add_record(session, employee, 100000, date(2024, 1, 1), ChangeType.raise_)
    _add_record(session, employee, 120000, date(2026, 12, 1), ChangeType.raise_)  # future relative to TODAY

    current = get_current_salary_record(session, employee.id, as_of=TODAY)

    assert current.id == past.id
    assert current.amount == 100000


def test_future_dated_record_becomes_current_once_its_date_arrives(session):
    employee = _make_employee(session)
    _add_record(session, employee, 100000, date(2024, 1, 1), ChangeType.raise_)
    future = _add_record(session, employee, 120000, date(2026, 12, 1), ChangeType.raise_)

    current = get_current_salary_record(session, employee.id, as_of=date(2026, 12, 1))

    assert current.id == future.id
    assert current.amount == 120000


def test_same_day_records_break_tie_by_most_recently_created(session):
    employee = _make_employee(session)
    _add_record(session, employee, 100000, date(2025, 1, 1), ChangeType.raise_)
    correction = _add_record(session, employee, 105000, date(2025, 1, 1), ChangeType.correction)

    current = get_current_salary_record(session, employee.id, as_of=TODAY)

    assert current.id == correction.id
    assert current.amount == 105000


def test_salary_history_includes_future_dated_records_ordered_newest_first(session):
    employee = _make_employee(session)
    hire = _add_record(session, employee, 90000, date(2020, 1, 1), ChangeType.hire)
    raise_ = _add_record(session, employee, 100000, date(2022, 1, 1), ChangeType.raise_)
    future = _add_record(session, employee, 120000, date(2026, 12, 1), ChangeType.raise_)

    history = get_salary_history(session, employee.id)

    assert [record.id for record in history] == [future.id, raise_.id, hire.id]