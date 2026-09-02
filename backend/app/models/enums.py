from enum import Enum

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum


class UserRole(str, Enum):
    admin = "admin"
    hr_manager = "hr_manager"
    executive_viewer = "executive_viewer"


class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"


class EmployeeStatus(str, Enum):
    active = "active"
    inactive = "inactive"


class ChangeType(str, Enum):
    hire = "hire"
    raise_ = "raise"
    promotion = "promotion"
    correction = "correction" # Fixes a wrong data entry. Kept as a new row (not an edit) to preserve history.
    cola = "cola" # Cost-Of-Living Adjustment: inflation-driven pay change, distinct from merit-based raises for payroll/budget reporting accuracy.


def enum_column(enum_cls: type[Enum], **kwargs) -> Column:
    """SQLAlchemy's Enum type persists by member *name* by default, not
    *value* — a silent mismatch whenever a member's name differs from its
    value (e.g. ChangeType.raise_ == "raise", since `raise` is a Python
    keyword). values_callable forces it to persist/compare on `.value`,
    matching the string values used throughout this app (API payloads,
    seed data, filters)."""
    return Column(SAEnum(enum_cls, values_callable=lambda cls: [e.value for e in cls]), **kwargs)