from datetime import date
from typing import Optional

from sqlmodel import SQLModel

from app.models.enums import ChangeType


class CountrySalaryStats(SQLModel):
    country: str
    headcount: int
    avg_salary_usd: float
    median_salary_usd: float


class DepartmentSalaryStats(SQLModel):
    department: str
    headcount: int
    avg_salary_usd: float
    median_salary_usd: float


class CountryPayroll(SQLModel):
    country: str
    headcount: int
    total_payroll_usd: float


class SalaryDistributionBand(SQLModel):
    band: str
    headcount: int


class GenderHeadcount(SQLModel):
    gender: str
    headcount: int


class GenderSalaryStats(SQLModel):
    gender: str
    headcount: int
    avg_salary_usd: Optional[float]
    suppressed: bool


class SalaryChangeFeedItem(SQLModel):
    employee_id: int
    employee_name: str
    department: str
    country: str
    change_type: ChangeType
    effective_date: date
    amount: float
    currency: str
    amount_usd: float


class QuarterlyPayroll(SQLModel):
    quarter: str
    headcount: int
    total_payroll_usd: float