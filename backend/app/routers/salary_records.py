from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db import get_session
from app.schemas.salary_record import SalaryRecordCreate, SalaryRecordRead
from app.services import employee as employee_service
from app.services.salary import create_salary_record, get_salary_history

router = APIRouter(prefix="/employees/{employee_id}/salary-records", tags=["salary-records"])


@router.post("", response_model=SalaryRecordRead, status_code=201)
def add_salary_record(
    employee_id: int, data: SalaryRecordCreate, session: Session = Depends(get_session)
):
    employee = employee_service.get_employee(session, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    try:
        return create_salary_record(session, employee, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("", response_model=list[SalaryRecordRead])
def list_salary_records(employee_id: int, session: Session = Depends(get_session)):
    employee = employee_service.get_employee(session, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    return get_salary_history(session, employee_id)