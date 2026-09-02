from sqlmodel import Session, func, or_, select

from app.models import Employee
from app.models.enums import EmployeeStatus
from app.schemas.employee import EmployeeCreate, EmployeeUpdate


def create_employee(session: Session, data: EmployeeCreate) -> Employee:
    employee = Employee.model_validate(data)
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee


def get_employee(session: Session, employee_id: int) -> Employee | None:
    return session.get(Employee, employee_id)


def _apply_filters(
    statement,
    *,
    country: str | None,
    department: str | None,
    role: str | None,
    status: EmployeeStatus | None,
    search: str | None,
):
    if country:
        statement = statement.where(Employee.country == country)
    if department:
        statement = statement.where(Employee.department == department)
    if role:
        statement = statement.where(Employee.role == role)
    if status:
        statement = statement.where(Employee.status == status)
    if search:
        like = f"%{search}%"
        statement = statement.where(or_(Employee.name.ilike(like), Employee.email.ilike(like)))
    return statement


def list_employees(
    session: Session,
    *,
    country: str | None = None,
    department: str | None = None,
    role: str | None = None,
    status: EmployeeStatus | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Employee], int]:
    filters = dict(country=country, department=department, role=role, status=status, search=search)

    count_statement = _apply_filters(select(func.count()).select_from(Employee), **filters)
    total = session.exec(count_statement).one()

    statement = _apply_filters(select(Employee), **filters)
    items = session.exec(statement.order_by(Employee.id).offset(skip).limit(limit)).all()

    return list(items), total


def update_employee(session: Session, employee: Employee, data: EmployeeUpdate) -> Employee:
    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(employee, field, value)
    session.add(employee)
    session.commit()
    session.refresh(employee)
    return employee