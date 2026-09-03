"""Bulk salary operations — apply a uniform % raise/COLA across a filtered
group of employees in one HR action. Each affected employee still gets an
individual, append-only SalaryRecord (never a shared/batch record) — same
current-salary-derivation rule as everywhere else, just triggered for many
employees at once instead of one at a time.

Restricted to change_type raise/cola: promotion is inherently individual
(it's paired with a specific new role — see SalaryRecordCreate.new_role),
and correction/hire are one-off, single-employee corrections, not the kind
of thing you'd ever want to apply identically across a whole department.

Always scoped to active employees — not a selectable filter. A raise for
someone who's already left the company isn't a "default that could be
overridden," it's never a real scenario, so it's enforced here rather than
left as a footgun some caller (UI or a direct API request) could pick
"inactive" or "all" for.

Percentage must be strictly positive — this is a *raise*, not a general
salary adjustment. A negative percentage would insert a SalaryRecord with
change_type "raise" (or "cola") whose amount is actually *lower* than the
prior one, which reads as self-contradictory in the salary history table.
requirements.md only ever asks for "apply a % raise"; a bulk pay-cut
feature (if ever needed) would need its own change_type concept, not a
sign flip on this one.
"""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Employee, SalaryRecord
from app.models.enums import ChangeType, EmployeeStatus
from app.services.currency import normalize_to_usd

ALLOWED_BULK_CHANGE_TYPES = (ChangeType.raise_, ChangeType.cola)


@dataclass(frozen=True)
class BulkRaiseResult:
    matched_count: int
    applied_count: int
    skipped_no_current_salary: int
    skipped_effective_date_before_hire: int


def _current_local_salary_subquery(as_of: date):
    """Like analytics._current_salary_subquery, but returns each employee's
    current *local* amount/currency rather than the USD snapshot — a bulk
    raise is applied to the local-currency figure the employee was last
    actually paid in, not a USD-converted one."""
    row_number = (
        func.row_number()
        .over(
            partition_by=SalaryRecord.employee_id,
            order_by=(SalaryRecord.effective_date.desc(), SalaryRecord.id.desc()),
        )
        .label("rn")
    )
    ranked = (
        select(SalaryRecord.employee_id, SalaryRecord.amount, SalaryRecord.currency, row_number)
        .where(SalaryRecord.effective_date <= as_of)
        .subquery()
    )
    return select(ranked).where(ranked.c.rn == 1).subquery()


def _apply_employee_filters(statement, *, country: str | None, department: str | None):
    # Always active — see module docstring.
    statement = statement.where(Employee.status == EmployeeStatus.active)
    if country:
        statement = statement.where(Employee.country == country)
    if department:
        statement = statement.where(Employee.department == department)
    return statement


def apply_bulk_raise(
    session: Session,
    *,
    percentage: float,
    effective_date: date,
    change_type: ChangeType = ChangeType.raise_,
    country: str | None = None,
    department: str | None = None,
) -> BulkRaiseResult:
    if change_type not in ALLOWED_BULK_CHANGE_TYPES:
        allowed = ", ".join(c.value for c in ALLOWED_BULK_CHANGE_TYPES)
        raise ValueError(f"Bulk updates only support change_type in [{allowed}]")
    if percentage <= 0:
        raise ValueError("percentage must be greater than 0 — this applies a raise, not a pay cut")

    matched_count = session.exec(
        _apply_employee_filters(select(func.count()).select_from(Employee), country=country, department=department)
    ).one()

    current = _current_local_salary_subquery(effective_date)
    statement = _apply_employee_filters(
        select(Employee.id, Employee.hire_date, current.c.amount, current.c.currency).join(
            current, current.c.employee_id == Employee.id
        ),
        country=country,
        department=department,
    )
    rows = session.execute(statement).all()

    new_records = []
    skipped_effective_date_before_hire = 0
    now = datetime.utcnow()

    for row in rows:
        if effective_date < row.hire_date:
            skipped_effective_date_before_hire += 1
            continue

        new_amount = round(row.amount * (1 + percentage / 100), 2)
        amount_usd_snapshot, fx_rate_to_usd = normalize_to_usd(new_amount, row.currency)
        new_records.append(
            {
                "employee_id": row.id,
                "amount": new_amount,
                "currency": row.currency,
                "amount_usd_snapshot": amount_usd_snapshot,
                "fx_rate_to_usd": fx_rate_to_usd,
                "effective_date": effective_date,
                "change_type": change_type.value,
                "created_at": now,
            }
        )

    if new_records:
        session.execute(SalaryRecord.__table__.insert(), new_records)
        session.commit()

    applied_count = len(new_records)
    return BulkRaiseResult(
        matched_count=matched_count,
        applied_count=applied_count,
        skipped_no_current_salary=matched_count - len(rows),
        skipped_effective_date_before_hire=skipped_effective_date_before_hire,
    )