from datetime import date

from app.db import engine, init_db
from app.models import Employee, SalaryRecord
from app.seed.generate import generate_employees, generate_salary_records

EMPLOYEE_COUNT = 10_000


def seed_core_data(count: int = EMPLOYEE_COUNT, today: date | None = None) -> tuple[int, int]:
    """Clears and repopulates Employee/SalaryRecord with correlated seed data.

    Clearing first (rather than appending) keeps re-running the script
    idempotent and reproducible given the fixed random seed.
    Returns (employee_count, salary_record_count).
    """
    today = today or date.today()
    init_db()

    employees = generate_employees(count, today)
    salary_records = generate_salary_records(employees, today)
    employee_rows = [e.to_row() for e in employees]

    with engine.begin() as conn:
        conn.execute(SalaryRecord.__table__.delete())
        conn.execute(Employee.__table__.delete())
        conn.execute(Employee.__table__.insert(), employee_rows)
        conn.execute(SalaryRecord.__table__.insert(), salary_records)

    return len(employee_rows), len(salary_records)