from app.models.enums import UserRole


def _csv_bytes(rows: list[str]) -> bytes:
    header = "name,email,country,department,role,gender,hire_date,status,amount,currency"
    return ("\n".join([header, *rows]) + "\n").encode("utf-8")


def test_import_csv_creates_employees(client):
    csv_bytes = _csv_bytes(
        ["Ada Lovelace,ada@acme.test,US,Engineering,Software Engineer,,2022-01-01,active,95000,USD"]
    )

    response = client.post(
        "/employees/import",
        files={"file": ("employees.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 1
    assert body["created_count"] == 1
    assert body["errors"] == []

    listed = client.get("/employees", params={"search": "Ada"}).json()
    assert listed["total"] == 1


def test_import_csv_requires_admin_or_hr_manager(client, make_token):
    token = make_token(UserRole.executive_viewer, email="exec@acme.test")
    csv_bytes = _csv_bytes(["Ada Lovelace,ada@acme.test,US,Engineering,Software Engineer,,2022-01-01,,,"])

    response = client.post(
        "/employees/import",
        files={"file": ("employees.csv", csv_bytes, "text/csv")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403