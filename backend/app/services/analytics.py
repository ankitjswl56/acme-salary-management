"""The 8 fixed analytics dashboard views (CLAUDE.md § Analytics).

Every "current state" view (1-6 below) is built on top of
get_current_salary_snapshots(): one employee = one row, using whichever
SalaryRecord is "current" as of `as_of` (default today), per the same
derived-not-stored rule as the CRUD detail endpoint. This is the single
place that rule is implemented for aggregation purposes, so the 8 views
(and the stretch NL-query feature, which calls these same functions) can't
drift from it or from each other.

Grouping/median is done in Python rather than pushed into SQL: SQLite has
no native MEDIAN aggregate, and at this data scale (10k employees) an
in-Python groupby is simpler to read, test, and port to another DB than a
per-view percentile-window query — see design-notes.md.
"""

import statistics
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Employee, SalaryRecord
from app.models.enums import EmployeeStatus


@dataclass(frozen=True)
class CurrentSalarySnapshot:
    employee_id: int
    country: str
    department: str
    role: str
    gender: str | None
    amount_usd: float
    effective_date: date
    change_type: str


def _current_salary_subquery(as_of: date):
    row_number = (
        func.row_number()
        .over(
            partition_by=SalaryRecord.employee_id,
            order_by=(SalaryRecord.effective_date.desc(), SalaryRecord.id.desc()),
        )
        .label("rn")
    )
    ranked = (
        select(
            SalaryRecord.employee_id,
            SalaryRecord.amount_usd_snapshot,
            SalaryRecord.effective_date,
            SalaryRecord.change_type,
            row_number,
        )
        .where(SalaryRecord.effective_date <= as_of)
        .subquery()
    )
    return select(ranked).where(ranked.c.rn == 1).subquery()


def get_current_salary_snapshots(
    session: Session, as_of: date | None = None, active_only: bool = True
) -> list[CurrentSalarySnapshot]:
    as_of = as_of or date.today()
    current = _current_salary_subquery(as_of)

    statement = select(
        Employee.id,
        Employee.country,
        Employee.department,
        Employee.role,
        Employee.gender,
        current.c.amount_usd_snapshot,
        current.c.effective_date,
        current.c.change_type,
    ).join(current, current.c.employee_id == Employee.id)

    if active_only:
        statement = statement.where(Employee.status == EmployeeStatus.active)

    rows = session.execute(statement).all()
    return [
        CurrentSalarySnapshot(
            employee_id=row.id,
            country=row.country,
            department=row.department,
            role=row.role,
            gender=row.gender.value if row.gender else None,
            amount_usd=row.amount_usd_snapshot,
            effective_date=row.effective_date,
            change_type=row.change_type.value,
        )
        for row in rows
    ]


def _group_by(snapshots: list[CurrentSalarySnapshot], key: str) -> dict[str, list[CurrentSalarySnapshot]]:
    groups: dict[str, list[CurrentSalarySnapshot]] = {}
    for snapshot in snapshots:
        groups.setdefault(getattr(snapshot, key), []).append(snapshot)
    return groups


def avg_median_salary_by_country(session: Session, as_of: date | None = None) -> list[dict]:
    snapshots = get_current_salary_snapshots(session, as_of)
    groups = _group_by(snapshots, "country")

    return [
        {
            "country": country,
            "headcount": len(group),
            "avg_salary_usd": round(statistics.mean(s.amount_usd for s in group), 2),
            "median_salary_usd": round(statistics.median(s.amount_usd for s in group), 2),
        }
        for country, group in sorted(groups.items())
    ]


def avg_median_salary_by_department(session: Session, as_of: date | None = None) -> list[dict]:
    snapshots = get_current_salary_snapshots(session, as_of)
    groups = _group_by(snapshots, "department")

    return [
        {
            "department": department,
            "headcount": len(group),
            "avg_salary_usd": round(statistics.mean(s.amount_usd for s in group), 2),
            "median_salary_usd": round(statistics.median(s.amount_usd for s in group), 2),
        }
        for department, group in sorted(groups.items())
    ]


def headcount_and_payroll_by_country(session: Session, as_of: date | None = None) -> list[dict]:
    snapshots = get_current_salary_snapshots(session, as_of)
    groups = _group_by(snapshots, "country")

    return [
        {
            "country": country,
            "headcount": len(group),
            "total_payroll_usd": round(sum(s.amount_usd for s in group), 2),
        }
        for country, group in sorted(groups.items())
    ]