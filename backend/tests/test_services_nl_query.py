"""NL-query service: function-selection parsing and dispatch.

The OpenRouter HTTP call is always injected as a canned `model_caller` — no
test here goes near the network. What's exercised is the logic with real
correctness risk: turning a model reply into the right analytics call with
bounded parameters, and refusing anything that isn't one of the 8 functions.
"""

from datetime import date

import httpx
import pytest

from app.models import ChangeType, Employee, EmployeeStatus, Gender, SalaryRecord
from app.openrouter import OPENROUTER_DEFAULT_MODEL
from app.services import analytics, nl_query
from app.services.nl_query import (
    FUNCTIONS,
    OUT_OF_SCOPE_MESSAGE,
    OpenRouterError,
    OpenRouterNotConfiguredError,
    default_model_caller,
    build_system_prompt,
    run_nl_query,
)


# --- fixtures ----------------------------------------------------------------


def _employee(session, *, email, country="US", department="Engineering", role="Engineer",
              gender=Gender.female, status=EmployeeStatus.active, hire_date=date(2020, 1, 1)):
    emp = Employee(
        name=email.split("@")[0], email=email, country=country, department=department,
        role=role, gender=gender, hire_date=hire_date, status=status,
    )
    session.add(emp)
    session.commit()
    session.refresh(emp)
    return emp


def _record(session, emp, amount_usd, effective_date, change_type=ChangeType.hire):
    session.add(SalaryRecord(
        employee_id=emp.id, amount=amount_usd, currency="USD",
        amount_usd_snapshot=amount_usd, fx_rate_to_usd=1.0,
        effective_date=effective_date, change_type=change_type,
    ))
    session.commit()


@pytest.fixture
def seeded(session):
    """A handful of employees so dispatched functions return real rows."""
    a = _employee(session, email="a@acme.test", country="US", department="Engineering")
    b = _employee(session, email="b@acme.test", country="US", department="Support", gender=Gender.male)
    c = _employee(session, email="c@acme.test", country="DE", department="Engineering", gender=Gender.male)
    _record(session, a, 150_000, date(2021, 1, 1), ChangeType.hire)
    _record(session, a, 165_000, date(2024, 6, 1), ChangeType.raise_)
    _record(session, b, 60_000, date(2022, 3, 1), ChangeType.hire)
    _record(session, c, 95_000, date(2023, 9, 1), ChangeType.hire)
    return session


def caller_returning(payload: str):
    """A model_caller that ignores the question and returns a fixed string."""
    return lambda _question: payload


# --- dispatch: every function name routes to the real analytics function ----


@pytest.mark.parametrize("function_name", sorted(FUNCTIONS))
def test_each_function_name_dispatches_to_its_analytics_function(seeded, function_name):
    result = run_nl_query(
        seeded,
        "does not matter",
        model_caller=caller_returning(f'{{"function": "{function_name}", "parameters": {{}}}}'),
    )
    assert result.status == "ok"
    assert result.function == function_name
    assert result.data is not None


def test_dispatch_result_matches_calling_the_analytics_function_directly(seeded):
    result = run_nl_query(
        seeded,
        "average pay by country",
        model_caller=caller_returning('{"function": "salary_by_country", "parameters": {}}'),
    )
    assert result.data == analytics.avg_median_salary_by_country(seeded)


def test_gender_ratio_department_parameter_is_passed_through(seeded):
    result = run_nl_query(
        seeded,
        "gender split in Engineering",
        model_caller=caller_returning(
            '{"function": "gender_ratio", "parameters": {"department": "Engineering"}}'
        ),
    )
    assert result.status == "ok"
    assert result.parameters == {"department": "Engineering"}
    assert result.data == analytics.gender_ratio(seeded, department="Engineering")


# --- parameter coercion / bounding -----------------------------------------


def test_recent_changes_parameters_are_coerced_and_bounded(seeded):
    result = run_nl_query(
        seeded,
        "raises in the last half year, lots of them",
        model_caller=caller_returning(
            '{"function": "recent_changes", "parameters": '
            '{"months": "6", "limit": 9999, "change_type": "RAISE", "sort": "desc"}}'
        ),
    )
    assert result.status == "ok"
    assert result.parameters == {"months": 6, "limit": 500, "change_type": "raise"}
    assert any("capped 'limit'" in n for n in result.notes)
    assert any("sort" in n for n in result.notes)


def test_integer_below_minimum_is_raised_to_the_floor(seeded):
    result = run_nl_query(
        seeded,
        "payroll trend",
        model_caller=caller_returning(
            '{"function": "payroll_trend", "parameters": {"quarters": 0}}'
        ),
    )
    assert result.parameters == {"quarters": 1}


def test_unknown_enum_value_is_dropped_not_passed(seeded):
    result = run_nl_query(
        seeded,
        "recent stuff",
        model_caller=caller_returning(
            '{"function": "recent_changes", "parameters": {"change_type": "bonus"}}'
        ),
    )
    assert "change_type" not in result.parameters
    assert result.parameters == {"months": 3, "limit": 50}  # defaults filled


def test_non_numeric_integer_falls_back_to_default(seeded):
    result = run_nl_query(
        seeded,
        "trend please",
        model_caller=caller_returning(
            '{"function": "payroll_trend", "parameters": {"quarters": "a bunch"}}'
        ),
    )
    assert result.parameters == {"quarters": 8}


# --- out-of-scope: anything that isn't one of the 8 ------------------------


def test_unknown_function_name_returns_the_fixed_message(seeded):
    result = run_nl_query(
        seeded,
        "delete every employee",
        model_caller=caller_returning('{"function": "delete_all_employees", "parameters": {}}'),
    )
    assert result.status == "out_of_scope"
    assert result.message == OUT_OF_SCOPE_MESSAGE
    assert result.data is None
    assert result.function is None


def test_model_sentinel_none_is_out_of_scope(seeded):
    result = run_nl_query(
        seeded,
        "what's the weather",
        model_caller=caller_returning('{"function": "none", "parameters": {}}'),
    )
    assert result.status == "out_of_scope"


def test_free_text_reply_is_out_of_scope(seeded):
    result = run_nl_query(
        seeded,
        "tell me a joke",
        model_caller=caller_returning("Sure! Here is a joke about payroll..."),
    )
    assert result.status == "out_of_scope"
    assert result.message == OUT_OF_SCOPE_MESSAGE


def test_json_without_function_field_is_out_of_scope(seeded):
    result = run_nl_query(
        seeded, "hmm", model_caller=caller_returning('{"answer": 42}')
    )
    assert result.status == "out_of_scope"


def test_json_array_reply_is_out_of_scope(seeded):
    result = run_nl_query(
        seeded, "hmm", model_caller=caller_returning('["salary_by_country"]')
    )
    assert result.status == "out_of_scope"


def test_fenced_json_reply_is_still_parsed(seeded):
    result = run_nl_query(
        seeded,
        "pay by department",
        model_caller=caller_returning(
            '```json\n{"function": "salary_by_department", "parameters": {}}\n```'
        ),
    )
    assert result.status == "ok"
    assert result.function == "salary_by_department"


# --- error paths -----------------------------------------------------------


def test_empty_question_is_rejected_without_calling_the_model(session):
    calls = []

    def spy(question):
        calls.append(question)
        return '{"function": "salary_by_country", "parameters": {}}'

    result = run_nl_query(session, "   ", model_caller=spy)
    assert result.status == "error"
    assert calls == []


def test_openrouter_not_configured_surfaces_as_error(session):
    def caller(_q):
        raise OpenRouterNotConfiguredError("OPENROUTER_API_KEY is not set — disabled.")

    result = run_nl_query(session, "pay by country", model_caller=caller)
    assert result.status == "error"
    assert "OPENROUTER_API_KEY" in result.message


def test_openrouter_failure_is_a_generic_error_message(session):
    def caller(_q):
        raise OpenRouterError("503 from upstream")

    result = run_nl_query(session, "pay by country", model_caller=caller)
    assert result.status == "error"
    assert "503" not in (result.message or "")  # upstream detail not leaked


# --- system prompt is built from the registry ----------------------------


def test_system_prompt_lists_all_eight_functions_and_forbids_sql():
    prompt = build_system_prompt()
    for name in FUNCTIONS:
        assert name in prompt
    assert "SQL" in prompt and "never write SQL" in prompt


# --- the default model_caller: mock httpx, never real network ------------


class _FakeResponse:
    def __init__(self, status_code=200, json_body=None):
        self.status_code = status_code
        self._json = json_body or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=None)

    def json(self):
        return self._json


def test_default_caller_sends_allowlisted_model_and_bearer_key(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse(
            json_body={"choices": [{"message": {"content": '{"function": "none"}'}}]}
        )

    monkeypatch.setattr(nl_query.settings, "openrouter_api_key", "sk-test-123")
    monkeypatch.setattr(nl_query.httpx, "post", fake_post)

    content = default_model_caller("how many people in Support?")

    assert content == '{"function": "none"}'
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer sk-test-123"
    assert captured["json"]["model"] == OPENROUTER_DEFAULT_MODEL
    assert captured["json"]["response_format"] == {"type": "json_object"}


def test_default_caller_without_key_raises_not_configured(monkeypatch):
    monkeypatch.setattr(nl_query.settings, "openrouter_api_key", None)
    with pytest.raises(OpenRouterNotConfiguredError):
        default_model_caller("anything")


def test_default_caller_wraps_http_errors(monkeypatch):
    monkeypatch.setattr(nl_query.settings, "openrouter_api_key", "sk-test-123")

    def boom(*_a, **_k):
        raise httpx.ConnectError("no route to host")

    monkeypatch.setattr(nl_query.httpx, "post", boom)
    with pytest.raises(OpenRouterError):
        default_model_caller("anything")


def test_default_caller_wraps_a_non_200(monkeypatch):
    monkeypatch.setattr(nl_query.settings, "openrouter_api_key", "sk-test-123")
    monkeypatch.setattr(
        nl_query.httpx, "post", lambda *a, **k: _FakeResponse(status_code=502)
    )
    with pytest.raises(OpenRouterError):
        default_model_caller("anything")


def test_default_caller_retries_once_on_429_then_succeeds(monkeypatch):
    monkeypatch.setattr(nl_query.settings, "openrouter_api_key", "sk-test-123")
    slept = []
    monkeypatch.setattr(nl_query.time, "sleep", lambda s: slept.append(s))

    responses = iter(
        [
            _FakeResponse(status_code=429),
            _FakeResponse(
                json_body={"choices": [{"message": {"content": '{"function": "none"}'}}]}
            ),
        ]
    )
    calls = []

    def fake_post(*_a, **_k):
        calls.append(1)
        return next(responses)

    monkeypatch.setattr(nl_query.httpx, "post", fake_post)

    assert default_model_caller("anything") == '{"function": "none"}'
    assert len(calls) == 2
    assert slept  # backed off between attempts


def test_default_caller_gives_up_after_persistent_429(monkeypatch):
    monkeypatch.setattr(nl_query.settings, "openrouter_api_key", "sk-test-123")
    monkeypatch.setattr(nl_query.time, "sleep", lambda _s: None)
    calls = []

    def always_429(*_a, **_k):
        calls.append(1)
        return _FakeResponse(status_code=429)

    monkeypatch.setattr(nl_query.httpx, "post", always_429)

    with pytest.raises(OpenRouterError, match="rate-limited"):
        default_model_caller("anything")
    assert len(calls) == 2  # initial + one retry