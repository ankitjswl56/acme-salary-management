from datetime import date, datetime

from sqlmodel import SQLModel

from app.models.enums import ChangeType


class SalaryRecordCreate(SQLModel):
    amount: float
    currency: str
    effective_date: date
    change_type: ChangeType


class SalaryRecordRead(SQLModel):
    id: int
    employee_id: int
    amount: float
    currency: str
    amount_usd_snapshot: float
    fx_rate_to_usd: float
    effective_date: date
    change_type: ChangeType
    created_at: datetime