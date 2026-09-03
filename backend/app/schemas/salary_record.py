from datetime import date, datetime
from typing import Optional

from sqlmodel import SQLModel

from app.models.enums import ChangeType


class SalaryRecordCreate(SQLModel):
    amount: float
    currency: str
    effective_date: date
    change_type: ChangeType
    # Set when this change also comes with a new title (typically a
    # promotion) - updates Employee.role in the same transaction as the
    # SalaryRecord, so the two can't drift out of sync (e.g. HR records the
    # raise but forgets to separately edit the title). Optional and not
    # restricted to change_type == promotion at the schema level - the
    # frontend only surfaces the field for promotions, but the backend
    # stays generically useful (e.g. a correction that also fixes a
    # wrongly-recorded title).
    new_role: Optional[str] = None


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