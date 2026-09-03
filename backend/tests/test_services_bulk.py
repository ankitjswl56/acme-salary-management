from datetime import date

import pytest

from app.models import ChangeType, Employee, EmployeeStatus, SalaryRecord
from app.services.bulk import apply_bulk_raise

TODAY = date(2026, 9, 2)


def _make_employee(session, **overrides) -> Employee:
    defaults = dict(
        name="Grace Hopper",
        email="grace@acme.test",
        country="US",
        department="Engineering",
        role="Senior Software Engineer",
        hire_date=date(2020, 1, 1),
        status=EmployeeStatus.active,
    )
    defaults.update(overrides)
    employee = Employee(**defaults)
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def _add_record(session, employee, amount, currency="USD", effective_date=date(2020, 1, 1), change_type=ChangeType.hire):
    record = SalaryRecord(
        employee_id=employee.id,
        amount=amount,
        currency=currency,
        amount_usd_snapshot=amount if currency == "USD" else amount * 1.27,
        fx_rate_to_usd=1.0 if currency == "USD" else 1.27,
        effective_date=effective_date,
        change_type=change_type,
    )
    session.add(record)
    session.commit()


def test_apply_bulk_raise_increases_salary_by_percentage(session):
    employee = _make_employee(session, email="a@acme.test")
    _add_record(session, employee, 100000)

    result = apply_bulk_raise(session, percentage=10, effective_date=TODAY)

    assert result.matched_count == 1
    assert result.applied_count == 1
    session.refresh(employee)
    current = employee.salary_records[-1]
    assert current.amount == 110000.0
    assert current.change_type == ChangeType.raise_


def test_apply_bulk_raise_applies_to_local_currency_not_usd(session):
    employee = _make_employee(session, email="a@acme.test")
    _add_record(session, employee, 1000, currency="GBP")

    apply_bulk_raise(session, percentage=10, effective_date=TODAY)

    session.refresh(employee)
    new_record = max(employee.salary_records, key=lambda r: r.id)
    assert new_record.currency == "GBP"
    assert new_record.amount == pytest.approx(1100.0)
    assert new_record.amount_usd_snapshot == pytest.approx(1100.0 * 1.27, rel=1e-3)


def test_apply_bulk_raise_filters_by_department(session):
    eng = _make_employee(session, email="eng@acme.test", department="Engineering")
    sales = _make_employee(session, email="sales@acme.test", department="Sales")
    _add_record(session, eng, 100000)
    _add_record(session, sales, 80000)

    result = apply_bulk_raise(session, percentage=10, effective_date=TODAY, department="Engineering")

    assert result.matched_count == 1
    assert result.applied_count == 1


def test_apply_bulk_raise_always_excludes_inactive_employees(session):
    """Not a default that could be overridden - there's no status
    parameter at all. A raise for someone who's already left the company
    isn't a real scenario, so it's not offered as a choice."""
    active = _make_employee(session, email="active@acme.test", status=EmployeeStatus.active)
    inactive = _make_employee(session, email="inactive@acme.test", status=EmployeeStatus.inactive)
    _add_record(session, active, 100000)
    _add_record(session, inactive, 100000)

    result = apply_bulk_raise(session, percentage=10, effective_date=TODAY)

    assert result.matched_count == 1
    assert result.applied_count == 1


def test_apply_bulk_raise_skips_employees_with_no_current_salary(session):
    _make_employee(session, email="a@acme.test")  # no salary record at all

    result = apply_bulk_raise(session, percentage=10, effective_date=TODAY)

    assert result.matched_count == 1
    assert result.applied_count == 0
    assert result.skipped_no_current_salary == 1


def test_apply_bulk_raise_skips_effective_date_before_hire(session):
    """Realistic via hire_date being corrected later than existing salary
    history (PATCH /employees/{id} allows editing hire_date freely) -
    the record must still be visible as "current" as of the bulk raise's
    effective_date for this check to even be reached (otherwise it's
    "no current salary" instead)."""
    employee = _make_employee(session, email="a@acme.test", hire_date=date(2020, 1, 1))
    _add_record(session, employee, 100000, effective_date=date(2020, 1, 1))
    employee.hire_date = date(2027, 1, 1)
    session.add(employee)
    session.commit()

    result = apply_bulk_raise(session, percentage=10, effective_date=date(2021, 1, 1))

    assert result.applied_count == 0
    assert result.skipped_effective_date_before_hire == 1


def test_apply_bulk_raise_rejects_invalid_change_type(session):
    with pytest.raises(ValueError, match="change_type"):
        apply_bulk_raise(session, percentage=10, effective_date=TODAY, change_type=ChangeType.promotion)


def test_apply_bulk_raise_rejects_zero_percentage(session):
    with pytest.raises(ValueError, match="percentage"):
        apply_bulk_raise(session, percentage=0, effective_date=TODAY)


def test_apply_bulk_raise_rejects_negative_percentage(session):
    """This is a *raise* - a negative percentage would insert a "raise"
    record whose amount is actually lower than the prior one, which reads
    as self-contradictory in the salary history table. A bulk pay-cut
    feature, if ever needed, is a different feature with its own
    change_type concept, not a sign flip on this one."""
    with pytest.raises(ValueError, match="percentage"):
        apply_bulk_raise(session, percentage=-10, effective_date=TODAY)


def test_apply_bulk_raise_does_not_affect_unmatched_employees(session):
    in_scope = _make_employee(session, email="in@acme.test", country="US")
    out_of_scope = _make_employee(session, email="out@acme.test", country="IN")
    _add_record(session, in_scope, 100000)
    _add_record(session, out_of_scope, 50000)

    apply_bulk_raise(session, percentage=10, effective_date=TODAY, country="US")

    session.refresh(out_of_scope)
    assert len(out_of_scope.salary_records) == 1  # unchanged, still just the original hire record