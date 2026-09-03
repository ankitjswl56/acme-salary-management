from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Index
from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import ChangeType, enum_column

if TYPE_CHECKING:
    from app.models.employee import Employee


class SalaryRecord(SQLModel, table=True):
    # Matches the current-salary window query's PARTITION BY employee_id
    # ORDER BY effective_date DESC - lets SQLite find each employee's latest
    # applicable record without scanning + sorting the whole history.
    __table_args__ = (
        Index("ix_salaryrecord_employee_effective", "employee_id", "effective_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    # No standalone index=True: employee_id is the leftmost column of the
    # composite index above, so a separate one is redundant write cost.
    employee_id: int = Field(foreign_key="employee.id")
    amount: float
    currency: str
    amount_usd_snapshot: float
    fx_rate_to_usd: float
    # Kept: recent-changes feed and the payroll trend scan on date alone.
    effective_date: date = Field(index=True)
    change_type: ChangeType = Field(sa_column=enum_column(ChangeType, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    employee: Optional["Employee"] = Relationship(back_populates="salary_records")
