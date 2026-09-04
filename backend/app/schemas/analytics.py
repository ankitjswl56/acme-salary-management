from datetime import date
from typing import Any, Optional

from pydantic import Field, field_validator
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


class NLQueryRequest(SQLModel):
    """A plain-English analytics question. The LLM maps it to one of the 8
    analytics functions — it never sees or writes SQL, and there is no write
    path behind this endpoint."""

    question: str = Field(min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def _reject_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must not be blank")
        return stripped


class NLQueryResponse(SQLModel):
    """Result of a natural-language query.

    status:
      - "ok": `function` was selected and run; `data` holds its output and
        `parameters` the (validated, bounded) arguments used.
      - "out_of_scope": the model's reply named no known analytics function;
        `message` is a fixed, polite refusal and `data` is null.
    (An "error" outcome — model unreachable / not configured — is returned as
    HTTP 503, not in this body.)
    """

    status: str
    question: str
    function: Optional[str] = None
    parameters: Optional[dict] = None
    data: Any = None
    message: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class AnalyticsDashboard(SQLModel):
    """Every view the dashboard renders on load, in one response. The three
    filterable views carry their default-parameter result; changing a filter
    on the frontend re-hits that view's own endpoint."""

    as_of: date
    salary_by_country: list[CountrySalaryStats]
    salary_by_department: list[DepartmentSalaryStats]
    headcount_payroll_by_country: list[CountryPayroll]
    salary_distribution: list[SalaryDistributionBand]
    salary_by_gender: list[GenderSalaryStats]
    gender_ratio: list[GenderHeadcount]
    recent_changes: list[SalaryChangeFeedItem]
    payroll_trend: list[QuarterlyPayroll]