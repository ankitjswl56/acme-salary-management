from enum import Enum


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