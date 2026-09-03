"""CSV import for onboarding batches of employees (requirements.md: "CSV
import for onboarding batches of employees — directly mirrors the brief's
framing of moving off Excel").

Each row is processed independently and reuses the exact same
create_employee() / create_salary_record() functions the single-employee
forms use, rather than re-implementing validation — so a CSV row is held
to identical rules (duplicate email, currency allowlist, effective_date
>= hire_date, etc.) and can't silently drift from them. One bad row
doesn't abort the batch: it's skipped and reported, not fatal to the rest
of the file.

amount/currency are optional per row; if both are given, an initial
"hire" SalaryRecord is created alongside the Employee (effective_date =
hire_date) — otherwise CSV-onboarded employees would all start with no
salary on record at all, same gap the single-employee create form has
always had, just multiplied across an entire batch.
"""

import csv
import io
from dataclasses import dataclass
from datetime import date

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.models.enums import ChangeType, EmployeeStatus, Gender
from app.schemas.employee import EmployeeCreate
from app.schemas.salary_record import SalaryRecordCreate
from app.services.employee import create_employee
from app.services.salary import create_salary_record

REQUIRED_COLUMNS = {"name", "email", "country", "department", "role", "hire_date"}


@dataclass(frozen=True)
class CsvImportRowError:
    row_number: int
    reason: str


@dataclass(frozen=True)
class CsvImportResult:
    total_rows: int
    created_count: int
    errors: list[CsvImportRowError]
    salary_warnings: list[CsvImportRowError]


def _field(row: dict[str, str | None], key: str) -> str:
    # A ragged row (fewer columns than the header) gives DictReader's
    # missing trailing values as None, not "" - guard against that here so
    # every row is at worst an empty string, never a None.strip() crash.
    return (row.get(key) or "").strip()


def _parse_employee(row: dict[str, str | None]) -> EmployeeCreate:
    gender_value = _field(row, "gender")
    status_value = _field(row, "status")

    return EmployeeCreate(
        name=_field(row, "name"),
        email=_field(row, "email"),
        country=_field(row, "country"),
        department=_field(row, "department"),
        role=_field(row, "role"),
        gender=Gender(gender_value) if gender_value else None,
        hire_date=date.fromisoformat(_field(row, "hire_date")),
        status=EmployeeStatus(status_value) if status_value else EmployeeStatus.active,
    )


def import_employees_csv(session: Session, file_contents: str) -> CsvImportResult:
    reader = csv.DictReader(io.StringIO(file_contents))

    if not reader.fieldnames:
        return CsvImportResult(0, 0, [CsvImportRowError(0, "CSV file is empty")], [])

    missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)
    if missing_columns:
        reason = f"Missing required column(s): {', '.join(sorted(missing_columns))}"
        return CsvImportResult(0, 0, [CsvImportRowError(0, reason)], [])

    total_rows = 0
    created_count = 0
    errors: list[CsvImportRowError] = []
    salary_warnings: list[CsvImportRowError] = []

    for row_number, row in enumerate(reader, start=1):
        total_rows += 1
        try:
            employee_data = _parse_employee(row)
            employee = create_employee(session, employee_data)
        except IntegrityError:
            session.rollback()
            errors.append(CsvImportRowError(row_number, "an employee with this email already exists"))
            continue
        except (ValueError, ValidationError, KeyError) as exc:
            session.rollback()
            errors.append(CsvImportRowError(row_number, str(exc)))
            continue

        created_count += 1

        amount_value = _field(row, "amount")
        currency_value = _field(row, "currency")
        if not amount_value and not currency_value:
            continue  # no starting salary provided for this row - allowed

        try:
            if not (amount_value and currency_value):
                raise ValueError("both amount and currency must be provided together, or neither")
            salary_data = SalaryRecordCreate(
                amount=float(amount_value),
                currency=currency_value,
                effective_date=employee_data.hire_date,
                change_type=ChangeType.hire,
            )
            create_salary_record(session, employee, salary_data)
        except (ValueError, ValidationError) as exc:
            salary_warnings.append(CsvImportRowError(row_number, str(exc)))

    return CsvImportResult(total_rows, created_count, errors, salary_warnings)