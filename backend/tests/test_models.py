from datetime import date, datetime

from app.models import (
    ChangeType,
    Employee,
    EmployeeStatus,
    Gender,
    SalaryRecord,
    User,
    UserRole,
)


def test_models_create_and_link_via_foreign_key(session):
    user = User(email="hr@acme.test", hashed_password="hashed", role=UserRole.hr_manager)
    employee = Employee(
        name="Ada Lovelace",
        email="ada@acme.test",
        country="UK",
        department="Engineering",
        role="Software Engineer",
        gender=Gender.female,
        hire_date=date(2020, 1, 15),
        status=EmployeeStatus.active,
    )
    session.add(user)
    session.add(employee)
    session.commit()
    session.refresh(employee)

    salary_record = SalaryRecord(
        employee_id=employee.id,
        amount=90000,
        currency="GBP",
        amount_usd_snapshot=112000,
        fx_rate_to_usd=1.244,
        effective_date=date(2020, 1, 15),
        change_type=ChangeType.hire,
    )
    session.add(salary_record)
    session.commit()
    session.refresh(salary_record)

    assert salary_record.id is not None
    assert salary_record.employee_id == employee.id
    assert salary_record.employee.name == "Ada Lovelace"
    assert employee.salary_records[0].amount == 90000
    assert isinstance(salary_record.created_at, datetime)


def test_salaryrecord_has_composite_employee_effective_index():
    # The current-salary window query depends on this composite index for
    # its partition/sort; assert it isn't dropped by accident.
    index_names = {ix.name for ix in SalaryRecord.__table__.indexes}
    assert "ix_salaryrecord_employee_effective" in index_names