from app.services.csv_import import import_employees_csv


def _csv(rows: list[str], header: str | None = None) -> str:
    header = header or "name,email,country,department,role,gender,hire_date,status,amount,currency"
    return "\n".join([header, *rows]) + "\n"


def test_import_creates_employee_and_hire_salary_record(session):
    csv_text = _csv(
        ["Ada Lovelace,ada@acme.test,US,Engineering,Software Engineer,female,2022-01-01,active,95000,USD"]
    )

    result = import_employees_csv(session, csv_text)

    assert result.total_rows == 1
    assert result.created_count == 1
    assert result.errors == []
    assert result.salary_warnings == []


def test_import_allows_a_row_with_no_salary_columns(session):
    csv_text = _csv(["Ada Lovelace,ada@acme.test,US,Engineering,Software Engineer,,2022-01-01,,,"])

    result = import_employees_csv(session, csv_text)

    assert result.created_count == 1
    assert result.salary_warnings == []


def test_import_rejects_missing_required_columns(session):
    csv_text = "name,email\nAda,ada@acme.test\n"

    result = import_employees_csv(session, csv_text)

    assert result.total_rows == 0
    assert result.created_count == 0
    assert len(result.errors) == 1
    assert "Missing required column" in result.errors[0].reason


def test_import_handles_an_empty_file(session):
    result = import_employees_csv(session, "")

    assert result.total_rows == 0
    assert result.created_count == 0
    assert len(result.errors) == 1


def test_import_reports_a_row_error_without_aborting_the_batch(session):
    csv_text = _csv(
        [
            "Ada Lovelace,ada@acme.test,US,Engineering,Software Engineer,,2022-01-01,,,",
            "Bad Date,bad@acme.test,US,Engineering,Software Engineer,,not-a-date,,,",
            "Grace Hopper,grace@acme.test,US,Engineering,Software Engineer,,2022-01-01,,,",
        ]
    )

    result = import_employees_csv(session, csv_text)

    assert result.total_rows == 3
    assert result.created_count == 2
    assert len(result.errors) == 1
    assert result.errors[0].row_number == 2


def test_import_reports_duplicate_email_within_the_same_file(session):
    csv_text = _csv(
        [
            "Ada Lovelace,ada@acme.test,US,Engineering,Software Engineer,,2022-01-01,,,",
            "Ada Impostor,ada@acme.test,US,Engineering,Software Engineer,,2022-01-01,,,",
        ]
    )

    result = import_employees_csv(session, csv_text)

    assert result.created_count == 1
    assert len(result.errors) == 1
    assert result.errors[0].row_number == 2
    assert "already exists" in result.errors[0].reason


def test_import_reports_invalid_currency_as_a_salary_warning_not_a_row_error(session):
    """The employee itself is still created - only the starting salary
    couldn't be recorded."""
    csv_text = _csv(
        ["Ada Lovelace,ada@acme.test,US,Engineering,Software Engineer,,2022-01-01,,95000,ZZZ"]
    )

    result = import_employees_csv(session, csv_text)

    assert result.created_count == 1
    assert result.errors == []
    assert len(result.salary_warnings) == 1
    assert result.salary_warnings[0].row_number == 1


def test_import_requires_amount_and_currency_together(session):
    csv_text = _csv(["Ada Lovelace,ada@acme.test,US,Engineering,Software Engineer,,2022-01-01,,95000,"])

    result = import_employees_csv(session, csv_text)

    assert result.created_count == 1
    assert len(result.salary_warnings) == 1
    assert "amount and currency" in result.salary_warnings[0].reason


def test_import_rejects_invalid_gender(session):
    csv_text = _csv(
        ["Ada Lovelace,ada@acme.test,US,Engineering,Software Engineer,not-a-gender,2022-01-01,,,"]
    )

    result = import_employees_csv(session, csv_text)

    assert result.created_count == 0
    assert len(result.errors) == 1