from datetime import date

import pytest

from app.models import ChangeType, Employee, EmployeeStatus, SalaryRecord
from app.schemas.salary_record import SalaryRecordCreate
from app.services.currency import InvalidAmountError, UnsupportedCurrencyError
from app.services.salary import create_salary_record, get_current_salary_record, get_salary_history

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


def test_create_salary_record_normalizes_currency_to_usd(session):
    employee = _make_employee(session)
    data = SalaryRecordCreate(
        amount=1000, currency="GBP", effective_date=date(2021, 1, 1), change_type=ChangeType.raise_
    )

    record = create_salary_record(session, employee, data)

    assert record.id is not None
    assert record.fx_rate_to_usd == pytest.approx(1.27)
    assert record.amount_usd_snapshot == pytest.approx(1270.0)


def test_create_salary_record_rejects_effective_date_before_hire(session):
    employee = _make_employee(session)  # hired 2020-01-01
    data = SalaryRecordCreate(
        amount=1000, currency="USD", effective_date=date(2019, 1, 1), change_type=ChangeType.hire
    )

    with pytest.raises(ValueError, match="hire_date"):
        create_salary_record(session, employee, data)


def test_create_salary_record_rejects_unsupported_currency(session):
    employee = _make_employee(session)
    data = SalaryRecordCreate(
        amount=1000, currency="XYZ", effective_date=date(2021, 1, 1), change_type=ChangeType.raise_
    )

    with pytest.raises(UnsupportedCurrencyError):
        create_salary_record(session, employee, data)


def test_create_salary_record_rejects_negative_amount(session):
    employee = _make_employee(session)
    data = SalaryRecordCreate(
        amount=-500, currency="USD", effective_date=date(2021, 1, 1), change_type=ChangeType.raise_
    )

    with pytest.raises(InvalidAmountError):
        create_salary_record(session, employee, data)


def test_create_salary_record_with_new_role_updates_employee(session):
    """A promotion's title change lands atomically with its pay change."""
    employee = _make_employee(session)  # role="Senior Software Engineer"
    data = SalaryRecordCreate(
        amount=1000,
        currency="USD",
        effective_date=date(2021, 1, 1),
        change_type=ChangeType.promotion,
        new_role="Staff Software Engineer",
    )

    create_salary_record(session, employee, data)

    session.refresh(employee)
    assert employee.role == "Staff Software Engineer"


def test_create_salary_record_without_new_role_leaves_employee_role_unchanged(session):
    employee = _make_employee(session)  # role="Senior Software Engineer"
    data = SalaryRecordCreate(
        amount=1000, currency="USD", effective_date=date(2021, 1, 1), change_type=ChangeType.raise_
    )

    create_salary_record(session, employee, data)

    session.refresh(employee)
    assert employee.role == "Senior Software Engineer"


def test_create_salary_record_allows_hire_as_the_first_record(session):
    employee = _make_employee(session)
    data = SalaryRecordCreate(
        amount=90000, currency="USD", effective_date=date(2020, 1, 1), change_type=ChangeType.hire
    )

    record = create_salary_record(session, employee, data)

    assert record.change_type == ChangeType.hire


def test_create_salary_record_rejects_a_second_hire(session):
    employee = _make_employee(session)
    create_salary_record(
        session,
        employee,
        SalaryRecordCreate(
            amount=90000, currency="USD", effective_date=date(2020, 1, 1), change_type=ChangeType.hire
        ),
    )

    with pytest.raises(ValueError, match="already has salary history"):
        create_salary_record(
            session,
            employee,
            SalaryRecordCreate(
                amount=95000, currency="USD", effective_date=date(2021, 1, 1), change_type=ChangeType.hire
            ),
        )


def test_create_salary_record_rejects_hire_after_a_non_hire_record_exists(session):
    """Even if the employee's only record isn't itself a "hire" (e.g. a
    correction backfilled first), a hire still can't be added second."""
    employee = _make_employee(session)
    create_salary_record(
        session,
        employee,
        SalaryRecordCreate(
            amount=90000, currency="USD", effective_date=date(2020, 1, 1), change_type=ChangeType.correction
        ),
    )

    with pytest.raises(ValueError, match="already has salary history"):
        create_salary_record(
            session,
            employee,
            SalaryRecordCreate(
                amount=90000, currency="USD", effective_date=date(2020, 1, 1), change_type=ChangeType.hire
            ),
        )