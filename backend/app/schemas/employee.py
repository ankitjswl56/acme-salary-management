from datetime import date
from typing import Optional

from sqlmodel import SQLModel

from app.models.enums import ChangeType, EmployeeStatus, Gender


class EmployeeCreate(SQLModel):
    name: str
    email: str
    country: str
    department: str
    role: str
    gender: Optional[Gender] = None
    hire_date: date
    status: EmployeeStatus = EmployeeStatus.active


class EmployeeUpdate(SQLModel):
    name: Optional[str] = None
    email: Optional[str] = None
    country: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    gender: Optional[Gender] = None
    hire_date: Optional[date] = None
    status: Optional[EmployeeStatus] = None


class EmployeeRead(SQLModel):
    id: int
    name: str
    email: str
    country: str
    department: str
    role: str
    gender: Optional[Gender]
    hire_date: date
    status: EmployeeStatus


class CurrentSalaryRead(SQLModel):
    amount: float
    currency: str
    amount_usd_snapshot: float
    effective_date: date
    change_type: ChangeType


class EmployeeDetail(EmployeeRead):
    current_salary: Optional[CurrentSalaryRead] = None


class EmployeeListResponse(SQLModel):
    total: int
    items: list[EmployeeRead]


class CountryOption(SQLModel):
    code: str
    name: str


class EmployeeFilterOptions(SQLModel):
    countries: list[CountryOption]
    departments: list[str]