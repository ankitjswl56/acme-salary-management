"""Current-salary resolution: "current" is always derived, never stored.

A SalaryRecord is never updated in place — every hire/raise/promotion/
correction/cola is a new row. "Current salary" is the latest record whose
effective_date has arrived (<= as_of), so a future-dated raise (e.g.
scheduled for next quarter) must NOT be treated as current until its date
actually arrives.
"""

from datetime import date

from sqlmodel import Session, select

from app.models import SalaryRecord


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
