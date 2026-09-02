"""Current-salary resolution: "current" is always derived, never stored.

A SalaryRecord is never updated in place — every hire/raise/promotion/
correction/cola is a new row. "Current salary" is the latest record whose
effective_date has arrived (<= as_of), so a future-dated raise (e.g.
scheduled for next quarter) must NOT be treated as current until its date
actually arrives.
"""

from datetime import date

from sqlmodel import Session, select

from app.models import Employee, SalaryRecord
from app.schemas.salary_record import SalaryRecordCreate
from app.services.currency import normalize_to_usd


def get_current_salary_record(
    session: Session, employee_id: int, as_of: date | None = None
) -> SalaryRecord | None:
    as_of = as_of or date.today()
    statement = (
        select(SalaryRecord)
        .where(SalaryRecord.employee_id == employee_id, SalaryRecord.effective_date <= as_of)
        .order_by(SalaryRecord.effective_date.desc(), SalaryRecord.id.desc())
        .limit(1)
    )
    return session.exec(statement).first()


def get_salary_history(session: Session, employee_id: int) -> list[SalaryRecord]:
    """Full history, most recent effective_date first (including future-dated
    records — this is an audit view, not the "current salary" resolution)."""
    statement = (
        select(SalaryRecord)
        .where(SalaryRecord.employee_id == employee_id)
        .order_by(SalaryRecord.effective_date.desc(), SalaryRecord.id.desc())
    )
    return list(session.exec(statement).all())


def create_salary_record(session: Session, employee: Employee, data: SalaryRecordCreate) -> SalaryRecord:
    """Appends a new SalaryRecord — never updates an existing one. currency
    amount validation and USD normalization is delegated to normalize_to_usd()
    (fixed FX rate, non-negative amount); the only check here is that a
    salary change can't predate the employee's hire."""
    if data.effective_date < employee.hire_date:
        raise ValueError("effective_date cannot be before the employee's hire_date")

    amount_usd_snapshot, fx_rate_to_usd = normalize_to_usd(data.amount, data.currency)

    record = SalaryRecord(
        employee_id=employee.id,
        amount=data.amount,
        currency=data.currency,
        amount_usd_snapshot=amount_usd_snapshot,
        fx_rate_to_usd=fx_rate_to_usd,
        effective_date=data.effective_date,
        change_type=data.change_type,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
