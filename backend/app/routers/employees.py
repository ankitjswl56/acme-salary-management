from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.db import get_session
from app.dependencies import require_role
from app.models.enums import EmployeeStatus, UserRole
from app.schemas.bulk import BulkRaiseRequest, BulkRaiseResponse
from app.schemas.csv_import import CsvImportResponse, CsvImportRowError
from app.schemas.employee import (
    CurrentSalaryRead,
    EmployeeCreate,
    EmployeeDetail,
    EmployeeFilterOptions,
    EmployeeListResponse,
    EmployeeRead,
    EmployeeUpdate,
)
from app.services import employee as employee_service
from app.services.bulk import apply_bulk_raise
from app.services.csv_import import import_employees_csv
from app.services.salary import get_current_salary_record

router = APIRouter(
    prefix="/employees",
    tags=["employees"],
    dependencies=[Depends(require_role(UserRole.admin, UserRole.hr_manager))],
)


@router.post("", response_model=EmployeeRead, status_code=201)
def create_employee(data: EmployeeCreate, session: Session = Depends(get_session)):
    try:
        return employee_service.create_employee(session, data)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="An employee with this email already exists")


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    country: Optional[str] = None,
    department: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[EmployeeStatus] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: Session = Depends(get_session),
):
    items, total = employee_service.list_employees(
        session,
        country=country,
        department=department,
        role=role,
        status=status,
        search=search,
        skip=skip,
        limit=limit,
    )
    return EmployeeListResponse(total=total, items=items)


@router.get("/filters", response_model=EmployeeFilterOptions)
def get_filter_options(session: Session = Depends(get_session)):
    """Distinct country/department values actually in use - registered
    before /{employee_id} so "filters" isn't swallowed as an employee_id
    path param."""
    countries, departments = employee_service.get_distinct_countries_and_departments(session)
    return EmployeeFilterOptions(countries=countries, departments=departments)


@router.post("/bulk-raise", response_model=BulkRaiseResponse)
def bulk_raise(data: BulkRaiseRequest, session: Session = Depends(get_session)):
    """Applies a uniform % raise/COLA to every employee matching the given
    filters - registered before /{employee_id} so "bulk-raise" isn't
    swallowed as an employee_id path param."""
    try:
        result = apply_bulk_raise(
            session,
            percentage=data.percentage,
            effective_date=data.effective_date,
            change_type=data.change_type,
            country=data.country,
            department=data.department,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return BulkRaiseResponse(
        matched_count=result.matched_count,
        applied_count=result.applied_count,
        skipped_no_current_salary=result.skipped_no_current_salary,
        skipped_effective_date_before_hire=result.skipped_effective_date_before_hire,
    )


@router.post("/import", response_model=CsvImportResponse)
async def import_employees(file: UploadFile = File(...), session: Session = Depends(get_session)):
    """Bulk-onboards employees from a CSV file - registered before
    /{employee_id} so "import" isn't swallowed as an employee_id path
    param. Each row is independent: a bad row is skipped and reported,
    not fatal to the rest of the file."""
    raw = await file.read()
    try:
        contents = raw.decode("utf-8-sig")  # utf-8-sig strips a BOM if present (common from Excel exports)
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 (or ASCII) encoded CSV text")

    result = import_employees_csv(session, contents)
    return CsvImportResponse(
        total_rows=result.total_rows,
        created_count=result.created_count,
        errors=[CsvImportRowError(row_number=e.row_number, reason=e.reason) for e in result.errors],
        salary_warnings=[
            CsvImportRowError(row_number=w.row_number, reason=w.reason) for w in result.salary_warnings
        ],
    )


@router.get("/{employee_id}", response_model=EmployeeDetail)
def get_employee(employee_id: int, session: Session = Depends(get_session)):
    employee = employee_service.get_employee(session, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    current = get_current_salary_record(session, employee_id)
    current_salary = (
        CurrentSalaryRead(
            amount=current.amount,
            currency=current.currency,
            amount_usd_snapshot=current.amount_usd_snapshot,
            effective_date=current.effective_date,
            change_type=current.change_type,
        )
        if current
        else None
    )
    return EmployeeDetail(**employee.model_dump(), current_salary=current_salary)


@router.patch("/{employee_id}", response_model=EmployeeRead)
def update_employee(employee_id: int, data: EmployeeUpdate, session: Session = Depends(get_session)):
    employee = employee_service.get_employee(session, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    try:
        return employee_service.update_employee(session, employee, data)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="An employee with this email already exists")