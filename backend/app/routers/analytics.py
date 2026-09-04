from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.db import get_session
from app.dependencies import get_current_user
from app.models.enums import ChangeType
from app.schemas.analytics import (
    AnalyticsDashboard,
    CountryPayroll,
    CountrySalaryStats,
    DepartmentSalaryStats,
    GenderHeadcount,
    GenderSalaryStats,
    NLQueryRequest,
    NLQueryResponse,
    QuarterlyPayroll,
    SalaryChangeFeedItem,
    SalaryDistributionBand,
)
from app.services import analytics as analytics_service
from app.services import nl_query as nl_query_service

# All three roles (admin, hr_manager, executive_viewer) can view analytics -
# it's the aggregate-only view executive_viewer is scoped to. So gating here
# just requires "logged in as anyone", not a specific role.
router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(get_current_user)])


@router.get("/dashboard", response_model=AnalyticsDashboard)
def dashboard(session: Session = Depends(get_session)):
    """One request for the whole dashboard. The 8 per-view endpoints below
    stay for the frontend's filter-driven refetches and the stretch
    NL-query feature."""
    return AnalyticsDashboard(**analytics_service.dashboard_summary(session))


def get_model_caller() -> nl_query_service.ModelCaller:
    """The OpenRouter caller the NL-query endpoint uses. Injected as a
    dependency so tests can override it with a canned function and never
    touch the network."""
    return nl_query_service.default_model_caller


@router.post("/ask", response_model=NLQueryResponse)
def ask(
    payload: NLQueryRequest,
    session: Session = Depends(get_session),
    model_caller: nl_query_service.ModelCaller = Depends(get_model_caller),
):
    """Natural-language analytics query. Read-only: the model only selects
    one of the 8 predefined analytics functions + typed params — it never
    generates SQL and there is no write path here. Same access rule as the
    rest of this router (any authenticated role, per Phase 5 RBAC)."""
    result = nl_query_service.run_nl_query(session, payload.question, model_caller=model_caller)
    if result.status == "error":
        # Model unreachable or not configured — a service-availability problem,
        # not a bad request. The polite in-scope refusal is status "ok"/"out_of_scope".
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result.message
        )
    return NLQueryResponse(**asdict(result))


@router.get("/salary-by-country", response_model=list[CountrySalaryStats])
def salary_by_country(session: Session = Depends(get_session)):
    return analytics_service.avg_median_salary_by_country(session)


@router.get("/salary-by-department", response_model=list[DepartmentSalaryStats])
def salary_by_department(session: Session = Depends(get_session)):
    return analytics_service.avg_median_salary_by_department(session)


@router.get("/headcount-payroll-by-country", response_model=list[CountryPayroll])
def headcount_payroll_by_country(session: Session = Depends(get_session)):
    return analytics_service.headcount_and_payroll_by_country(session)


@router.get("/salary-distribution", response_model=list[SalaryDistributionBand])
def salary_distribution(session: Session = Depends(get_session)):
    return analytics_service.salary_distribution(session)


@router.get("/gender-ratio", response_model=list[GenderHeadcount])
def gender_ratio(department: Optional[str] = None, session: Session = Depends(get_session)):
    return analytics_service.gender_ratio(session, department=department)


@router.get("/salary-by-gender", response_model=list[GenderSalaryStats])
def salary_by_gender(
    department: Optional[str] = None,
    role: Optional[str] = None,
    min_group_size: int = Query(analytics_service.DEFAULT_MIN_GROUP_SIZE, ge=1),
    session: Session = Depends(get_session),
):
    return analytics_service.avg_salary_by_gender(
        session, department=department, role=role, min_group_size=min_group_size
    )


@router.get("/recent-changes", response_model=list[SalaryChangeFeedItem])
def recent_changes(
    months: int = Query(3, ge=1, le=24),
    change_type: Optional[ChangeType] = None,
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    return analytics_service.recent_changes_feed(session, months=months, change_type=change_type, limit=limit)


@router.get("/payroll-trend", response_model=list[QuarterlyPayroll])
def payroll_trend(
    quarters: int = Query(8, ge=1, le=40),
    session: Session = Depends(get_session),
):
    return analytics_service.payroll_trend_by_quarter(session, quarters=quarters)