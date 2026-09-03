from sqlmodel import SQLModel


class CsvImportRowError(SQLModel):
    row_number: int
    reason: str


class CsvImportResponse(SQLModel):
    total_rows: int
    created_count: int
    # Row failed entirely - no employee was created.
    errors: list[CsvImportRowError]
    # Employee WAS created, but the row's amount/currency (if any) failed
    # validation, so no initial salary record exists yet - not a failure of
    # the row overall, since the employee import itself still succeeded.
    salary_warnings: list[CsvImportRowError]