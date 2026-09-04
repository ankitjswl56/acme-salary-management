"""POST /analytics/ask — the NL-query endpoint.

The OpenRouter caller is overridden with a canned function (via the
get_model_caller dependency), so these tests are deterministic and offline.
They cover the HTTP contract and the RBAC boundary; the selection/dispatch
logic itself is covered in test_services_nl_query.py.
"""

import pytest

from app.main import app
from app.models.enums import UserRole
from app.routers import analytics as analytics_router
from app.services.nl_query import OpenRouterError, OpenRouterNotConfiguredError

SALARY_BY_COUNTRY = '{"function": "salary_by_country", "parameters": {}}'


@pytest.fixture
def set_caller():
    """Install a canned model_caller for the endpoint; cleaned up after."""

    def _install(caller):
        app.dependency_overrides[analytics_router.get_model_caller] = lambda: caller

    yield _install
    app.dependency_overrides.pop(analytics_router.get_model_caller, None)


def _returning(payload):
    return lambda _question: payload


def _raising(exc):
    def _caller(_question):
        raise exc

    return _caller


# --- RBAC: same rule as the rest of /analytics ------------------------------


def test_ask_requires_auth(unauthenticated_client, set_caller):
    set_caller(_returning(SALARY_BY_COUNTRY))
    response = unauthenticated_client.post("/analytics/ask", json={"question": "pay by country?"})
    assert response.status_code == 401


def test_hr_manager_can_ask(client, set_caller):
    """`client` is hr_manager-authenticated by default."""
    set_caller(_returning(SALARY_BY_COUNTRY))
    response = client.post("/analytics/ask", json={"question": "average pay by country"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_executive_viewer_can_ask(client, make_token, set_caller):
    set_caller(_returning(SALARY_BY_COUNTRY))
    token = make_token(UserRole.executive_viewer, email="exec@acme.test")
    response = client.post(
        "/analytics/ask",
        json={"question": "average pay by country"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_admin_can_ask(client, make_token, set_caller):
    set_caller(_returning(SALARY_BY_COUNTRY))
    token = make_token(UserRole.admin, email="admin@acme.test")
    response = client.post(
        "/analytics/ask",
        json={"question": "average pay by country"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


# --- response contract ----------------------------------------------------


def test_ok_response_carries_function_params_and_data(client, set_caller):
    set_caller(_returning('{"function": "payroll_trend", "parameters": {"quarters": 999}}'))
    response = client.post("/analytics/ask", json={"question": "payroll trend all time"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["function"] == "payroll_trend"
    assert body["parameters"] == {"quarters": 40}  # bounded
    assert isinstance(body["data"], list) and body["data"]
    assert any("capped 'quarters'" in note for note in body["notes"])


def test_out_of_scope_question_is_200_with_fixed_message(client, set_caller):
    set_caller(_returning("Here's a haiku about compensation instead."))
    response = client.post("/analytics/ask", json={"question": "write me a poem"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "out_of_scope"
    assert "salary data" in body["message"]
    assert body["data"] is None
    assert body["function"] is None


def test_unknown_function_name_cannot_reach_a_write(client, set_caller):
    # Even if the model "asks" for a destructive action, there's no such
    # function in the registry — it's just an out-of-scope reply.
    set_caller(_returning('{"function": "delete_all_employees", "parameters": {}}'))
    response = client.post("/analytics/ask", json={"question": "wipe the database"})

    assert response.status_code == 200
    assert response.json()["status"] == "out_of_scope"


# --- error mapping -------------------------------------------------------


def test_model_not_configured_returns_503(client, set_caller):
    set_caller(_raising(OpenRouterNotConfiguredError("OPENROUTER_API_KEY is not set — disabled.")))
    response = client.post("/analytics/ask", json={"question": "pay by country"})

    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]


def test_model_unreachable_returns_503_without_leaking_detail(client, set_caller):
    set_caller(_raising(OpenRouterError("connect timeout to 1.2.3.4")))
    response = client.post("/analytics/ask", json={"question": "pay by country"})

    assert response.status_code == 503
    assert "1.2.3.4" not in response.json()["detail"]


# --- request validation -------------------------------------------------


def test_blank_question_is_422(client, set_caller):
    set_caller(_returning(SALARY_BY_COUNTRY))
    response = client.post("/analytics/ask", json={"question": "   "})
    assert response.status_code == 422


def test_missing_question_is_422(client, set_caller):
    set_caller(_returning(SALARY_BY_COUNTRY))
    response = client.post("/analytics/ask", json={})
    assert response.status_code == 422


def test_overlong_question_is_422(client, set_caller):
    set_caller(_returning(SALARY_BY_COUNTRY))
    response = client.post("/analytics/ask", json={"question": "x" * 501})
    assert response.status_code == 422