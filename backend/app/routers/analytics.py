from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db import get_session
from app.models.enums import ChangeType
from app.schemas.analytics import (
    CountryPayroll,
    CountrySalaryStats,
    DepartmentSalaryStats,
    GenderHeadcount,
    GenderSalaryStats,
    QuarterlyPayroll,
    SalaryChangeFeedItem,
    SalaryDistributionBand,
)
from app.services import analytics as analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


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