from datetime import date
from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import EmployeeStatus, Gender

if TYPE_CHECKING:
    from app.models.salary_record import SalaryRecord


class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(index=True, unique=True)
    country: str = Field(index=True)
    department: str = Field(index=True)
    role: str
    gender: Optional[Gender] = None
    hire_date: date
    status: EmployeeStatus = Field(default=EmployeeStatus.active, index=True)

    salary_records: List["SalaryRecord"] = Relationship(back_populates="employee")
