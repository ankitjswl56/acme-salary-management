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

import calendar
import statistics
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Employee, SalaryRecord
from app.models.enums import ChangeType, EmployeeStatus


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


SALARY_DISTRIBUTION_BANDS: list[tuple[float, float, str]] = [
    (0, 30_000, "<$30k"),
    (30_000, 50_000, "$30k-$50k"),
    (50_000, 75_000, "$50k-$75k"),
    (75_000, 100_000, "$75k-$100k"),
    (100_000, 125_000, "$100k-$125k"),
    (125_000, 150_000, "$125k-$150k"),
    (150_000, 200_000, "$150k-$200k"),
    (200_000, float("inf"), "$200k+"),
]


def salary_distribution(session: Session, as_of: date | None = None) -> list[dict]:
    """Org-wide histogram of current USD salary, in fixed bands. Every band
    is included even with zero headcount, so a chart doesn't have gaps."""
    snapshots = get_current_salary_snapshots(session, as_of)

    counts = {label: 0 for _, _, label in SALARY_DISTRIBUTION_BANDS}
    for snapshot in snapshots:
        for lower, upper, label in SALARY_DISTRIBUTION_BANDS:
            if lower <= snapshot.amount_usd < upper:
                counts[label] += 1
                break

    return [{"band": label, "headcount": counts[label]} for _, _, label in SALARY_DISTRIBUTION_BANDS]


def gender_ratio(session: Session, department: str | None = None, active_only: bool = True) -> list[dict]:
    """Headcount by gender — always safe to show at any group size, since
    it's a count, not a figure derived from individuals' pay."""
    statement = select(Employee.gender, func.count()).group_by(Employee.gender)
    if active_only:
        statement = statement.where(Employee.status == EmployeeStatus.active)
    if department:
        statement = statement.where(Employee.department == department)

    rows = session.execute(statement).all()
    return [
        {"gender": gender.value if gender else "unspecified", "headcount": headcount}
        for gender, headcount in rows
    ]


DEFAULT_MIN_GROUP_SIZE = 5


def avg_salary_by_gender(
    session: Session,
    department: str | None = None,
    role: str | None = None,
    as_of: date | None = None,
    min_group_size: int = DEFAULT_MIN_GROUP_SIZE,
) -> list[dict]:
    """Average current USD salary by gender, within an optional department/
    role scope. A group's average is suppressed (avg_salary_usd = None) when
    its headcount is below min_group_size, since — unlike headcount — an
    average derived from a handful of individuals' pay risks indirectly
    exposing one person's salary. Enforced here in the query layer, not left
    to the frontend to hide."""
    snapshots = get_current_salary_snapshots(session, as_of)
    if department:
        snapshots = [s for s in snapshots if s.department == department]
    if role:
        snapshots = [s for s in snapshots if s.role == role]

    groups: dict[str, list[CurrentSalarySnapshot]] = {}
    for snapshot in snapshots:
        groups.setdefault(snapshot.gender or "unspecified", []).append(snapshot)

    results = []
    for gender, group in sorted(groups.items()):
        headcount = len(group)
        suppressed = headcount < min_group_size
        results.append(
            {
                "gender": gender,
                "headcount": headcount,
                "avg_salary_usd": None if suppressed else round(statistics.mean(s.amount_usd for s in group), 2),
                "suppressed": suppressed,
            }
        )
    return results


def _months_ago(reference: date, months: int) -> date:
    month_index = reference.month - 1 - months
    year = reference.year + month_index // 12
    month = month_index % 12 + 1
    day = min(reference.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def recent_changes_feed(
    session: Session,
    months: int = 3,
    change_type: ChangeType | None = None,
    as_of: date | None = None,
    limit: int = 50,
) -> list[dict]:
    """Raw SalaryRecord feed, not the "current salary" resolution — an HR
    ops/audit view of what actually changed recently, regardless of the
    employee's current active status."""
    as_of = as_of or date.today()
    cutoff = _months_ago(as_of, months)

    statement = (
        select(SalaryRecord, Employee)
        .join(Employee, Employee.id == SalaryRecord.employee_id)
        .where(SalaryRecord.effective_date >= cutoff, SalaryRecord.effective_date <= as_of)
        .order_by(SalaryRecord.effective_date.desc(), SalaryRecord.id.desc())
        .limit(limit)
    )
    if change_type:
        statement = statement.where(SalaryRecord.change_type == change_type)

    rows = session.execute(statement).all()
    return [
        {
            "employee_id": employee.id,
            "employee_name": employee.name,
            "department": employee.department,
            "country": employee.country,
            "change_type": record.change_type.value,
            "effective_date": record.effective_date,
            "amount": record.amount,
            "currency": record.currency,
            "amount_usd": record.amount_usd_snapshot,
        }
        for record, employee in rows
    ]


def _quarter_end_dates(as_of: date, count: int) -> list[tuple[str, date]]:
    year, quarter = as_of.year, (as_of.month - 1) // 3 + 1
    quarters: list[tuple[str, date]] = []
    for _ in range(count):
        month = quarter * 3
        day = calendar.monthrange(year, month)[1]
        quarters.append((f"{year}-Q{quarter}", date(year, month, day)))
        quarter -= 1
        if quarter == 0:
            quarter, year = 4, year - 1
    return list(reversed(quarters))  # oldest first


def payroll_trend_by_quarter(session: Session, quarters: int = 8, as_of: date | None = None) -> list[dict]:
    """Total payroll cost per quarter, over the last `quarters` quarters
    (including the current, partial one).

    Uses active_only=False: this is a historical view, and Employee.status
    only tells us who's active *now* — it can't tell us who was active in a
    past quarter (there's no tracked termination date), so status isn't a
    meaningful filter here. An employee counts toward a quarter if they had
    an applicable SalaryRecord by that quarter's end (or by `as_of` for the
    current, still-in-progress quarter — never further ahead than "today",
    so an already-scheduled future raise can't inflate the current quarter
    before it actually takes effect).
    """
    as_of = as_of or date.today()

    results = []
    for label, quarter_end in _quarter_end_dates(as_of, quarters):
        snapshots = get_current_salary_snapshots(session, as_of=min(quarter_end, as_of), active_only=False)
        results.append(
            {
                "quarter": label,
                "headcount": len(snapshots),
                "total_payroll_usd": round(sum(s.amount_usd for s in snapshots), 2),
            }
        )
    return results