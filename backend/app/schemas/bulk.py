from datetime import date
from typing import Optional

from sqlmodel import SQLModel

from app.models.enums import ChangeType


class BulkRaiseRequest(SQLModel):
    percentage: float
    effective_date: date
    change_type: ChangeType = ChangeType.raise_
    country: Optional[str] = None
    department: Optional[str] = None
    # No status field: bulk raises are always scoped to active employees,
    # not a selectable filter — see app/services/bulk.py.


class BulkRaiseResponse(SQLModel):
    matched_count: int
    applied_count: int
    skipped_no_current_salary: int
    skipped_effective_date_before_hire: int