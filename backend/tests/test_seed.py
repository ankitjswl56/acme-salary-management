from datetime import date

from app.models import Employee
from app.seed import run as seed_run


def _make_employee(session):
    employee = Employee(
        name="Existing Person",
        email="existing@acme.test",
        country="US",
        department="Engineering",
        role="Engineer",
        hire_date=date(2020, 1, 1),
    )
    session.add(employee)
    session.commit()


def test_seed_if_empty_skips_when_employees_already_exist(session, monkeypatch):
    """The startup auto-seed must be a no-op on a DB that already has data,
    so restarting the container never duplicates or resets the dataset."""
    _make_employee(session)

    calls = []
    monkeypatch.setattr(seed_run, "seed_core_data", lambda *a, **k: calls.append("core"))
    monkeypatch.setattr(seed_run, "seed_demo_users", lambda *a, **k: calls.append("users"))

    did_seed = seed_run.seed_if_empty(session)

    assert did_seed is False
    assert calls == []


def test_seed_if_empty_runs_when_no_employees(session, monkeypatch):
    """On a fresh, empty DB the same call does seed both core data and the
    demo users."""
    calls = []
    monkeypatch.setattr(seed_run, "seed_core_data", lambda *a, **k: calls.append("core"))
    monkeypatch.setattr(seed_run, "seed_demo_users", lambda *a, **k: calls.append("users"))

    did_seed = seed_run.seed_if_empty(session)

    assert did_seed is True
    assert calls == ["core", "users"]