from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import ChangeType, enum_column

if TYPE_CHECKING:
    from app.models.employee import Employee


class SalaryRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: int = Field(foreign_key="employee.id", index=True)
    amount: float
    currency: str
    amount_usd_snapshot: float
    fx_rate_to_usd: float
    effective_date: date = Field(index=True)
    change_type: ChangeType = Field(sa_column=enum_column(ChangeType, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    employee: Optional["Employee"] = Relationship(back_populates="salary_records")
