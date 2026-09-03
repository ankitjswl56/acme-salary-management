from datetime import date

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Employee, SalaryRecord, User
from app.seed.generate import generate_employees, generate_salary_records
from app.seed.users import generate_demo_user_rows

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


def seed_demo_users() -> int:
    """Clears and reseeds the 3 demo accounts (one per role, shared password)."""
    init_db()

    user_rows = generate_demo_user_rows()

    with engine.begin() as conn:
        conn.execute(User.__table__.delete())
        conn.execute(User.__table__.insert(), user_rows)

    return len(user_rows)


def seed_if_empty(session: Session | None = None) -> bool:
    """Seed core data + demo users, but only when the Employee table is empty.

    Called from the app lifespan on startup so a bare `docker compose up`
    produces a fully seeded environment with no manual seed step. Because it
    checks first and does nothing when data already exists, it's safe to run
    on every container restart — it won't duplicate or reset an existing
    dataset. Use the standalone `python -m app.seed` script to force a
    re-seed during development.

    Returns True if seeding ran, False if it was skipped.
    """
    own_session = session is None
    if own_session:
        init_db()
        session = Session(engine)
    try:
        if session.exec(select(Employee.id).limit(1)).first() is not None:
            return False
    finally:
        if own_session:
            session.close()

    seed_core_data()
    seed_demo_users()
    return True