"""Natural-language analytics query (CLAUDE.md § Stretch feature).

Read-only, analytics-only, **no write path, ever**. HR types a question in
plain English; an LLM maps it to exactly one of the 8 predefined analytics
functions (function-selection style: the model returns a function name + typed
parameters as JSON, never SQL, never free text). The backend then runs the
*real*, already-tested analytics function and returns its actual result.

Design points that matter:

- The LLM chooses from a fixed registry (``FUNCTION_SPECS``). If its answer
  doesn't name one of those 8, the user gets a fixed "I can only answer
  questions about salary data" reply — the model never answers freeform.
- The model's parameters are coerced and bounded here (same limits as the
  REST endpoints), so a bad value degrades to the default instead of
  reaching a query function unchecked.
- The one external seam — the OpenRouter HTTP call — is injected as
  ``model_caller``. Tests pass a canned function; nothing in the test suite
  touches the network.
- Compensation *changes* (raises, edits, new employees) are deliberately not
  reachable from here. Those stay in explicit, human-confirmed UI forms —
  a pay change warrants a deliberate decision, not a sentence parsed by a
  model. See docs/design-notes.md.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlmodel import Session

from app.config import settings
from app.models.enums import ChangeType
from app.openrouter import OPENROUTER_BASE_URL, resolve_openrouter_model
from app.services import analytics

OUT_OF_SCOPE_MESSAGE = (
    "I can only answer questions about salary data — try asking about pay by "
    "country or department, headcount and payroll, gender pay balance, recent "
    "salary changes, or the payroll trend."
)

# The reply itself is short JSON, but the default model is a reasoning model
# that spends completion tokens thinking before it emits the object, so leave
# headroom or the JSON gets truncated mid-object.
_MODEL_TIMEOUT_SECONDS = 20.0
_MODEL_MAX_TOKENS = 600

# Free models share an upstream pool and 429 intermittently ("retry shortly").
# One retry turns most of those into a successful call instead of a 503.
_MODEL_RETRY_ON_429 = 1
_MODEL_RETRY_BACKOFF_SECONDS = 2.0


class OpenRouterNotConfiguredError(RuntimeError):
    """No OPENROUTER_API_KEY — the feature is switched off rather than broken."""


class OpenRouterError(RuntimeError):
    """The OpenRouter call failed or returned something unparseable."""


class SelectionParseError(ValueError):
    """The model's reply wasn't the JSON function-selection shape we asked for."""


# --- the fixed function registry -------------------------------------------------

_CHANGE_TYPES: tuple[str, ...] = tuple(ct.value for ct in ChangeType)


@dataclass(frozen=True)
class ParamSpec:
    type: str  # "string" | "integer" | "enum"
    description: str
    minimum: int | None = None
    maximum: int | None = None
    enum: tuple[str, ...] | None = None
    default: Any = None


@dataclass(frozen=True)
class QueryFunctionSpec:
    name: str
    description: str
    parameters: dict[str, ParamSpec]
    runner: Callable[[Session, dict], Any]


def _run_salary_by_country(session: Session, _params: dict) -> Any:
    return analytics.avg_median_salary_by_country(session)


def _run_salary_by_department(session: Session, _params: dict) -> Any:
    return analytics.avg_median_salary_by_department(session)


def _run_headcount_payroll_by_country(session: Session, _params: dict) -> Any:
    return analytics.headcount_and_payroll_by_country(session)


def _run_salary_distribution(session: Session, _params: dict) -> Any:
    return analytics.salary_distribution(session)


def _run_gender_ratio(session: Session, params: dict) -> Any:
    return analytics.gender_ratio(session, department=params.get("department"))


def _run_salary_by_gender(session: Session, params: dict) -> Any:
    return analytics.avg_salary_by_gender(
        session, department=params.get("department"), role=params.get("role")
    )


def _run_recent_changes(session: Session, params: dict) -> Any:
    raw_change_type = params.get("change_type")
    change_type = ChangeType(raw_change_type) if raw_change_type else None
    return analytics.recent_changes_feed(
        session,
        months=params.get("months", 3),
        change_type=change_type,
        limit=params.get("limit", 50),
    )


def _run_payroll_trend(session: Session, params: dict) -> Any:
    return analytics.payroll_trend_by_quarter(session, quarters=params.get("quarters", 8))


FUNCTION_SPECS: list[QueryFunctionSpec] = [
    QueryFunctionSpec(
        name="salary_by_country",
        description="Average and median current salary (USD) per country, with headcount.",
        parameters={},
        runner=_run_salary_by_country,
    ),
    QueryFunctionSpec(
        name="salary_by_department",
        description="Average and median current salary (USD) per department, with headcount.",
        parameters={},
        runner=_run_salary_by_department,
    ),
    QueryFunctionSpec(
        name="headcount_payroll_by_country",
        description="Headcount and total annual payroll cost (USD) per country.",
        parameters={},
        runner=_run_headcount_payroll_by_country,
    ),
    QueryFunctionSpec(
        name="salary_distribution",
        description="Org-wide count of employees in each salary band (USD).",
        parameters={},
        runner=_run_salary_distribution,
    ),
    QueryFunctionSpec(
        name="gender_ratio",
        description="Headcount by gender, org-wide or within one department. Always safe to show.",
        parameters={
            "department": ParamSpec(
                "string",
                "Restrict to this department name (e.g. 'Engineering'). Omit for org-wide.",
            ),
        },
        runner=_run_gender_ratio,
    ),
    QueryFunctionSpec(
        name="salary_by_gender",
        description=(
            "Average current salary (USD) by gender, optionally within a department "
            "and/or job role. Groups below the minimum size are withheld for privacy."
        ),
        parameters={
            "department": ParamSpec("string", "Restrict to this department name. Optional."),
            "role": ParamSpec("string", "Restrict to this job role/title. Optional."),
        },
        runner=_run_salary_by_gender,
    ),
    QueryFunctionSpec(
        name="recent_changes",
        description="Feed of recent salary-change records (hire, raise, promotion, correction, cola).",
        parameters={
            "months": ParamSpec(
                "integer", "How many months back to include.", minimum=1, maximum=24, default=3
            ),
            "change_type": ParamSpec(
                "enum", "Restrict to a single change type.", enum=_CHANGE_TYPES
            ),
            "limit": ParamSpec(
                "integer", "Maximum number of rows.", minimum=1, maximum=500, default=50
            ),
        },
        runner=_run_recent_changes,
    ),
    QueryFunctionSpec(
        name="payroll_trend",
        description="Total payroll cost (USD) per quarter over the last N quarters.",
        parameters={
            "quarters": ParamSpec(
                "integer", "How many quarters to include.", minimum=1, maximum=40, default=8
            ),
        },
        runner=_run_payroll_trend,
    ),
]

FUNCTIONS: dict[str, QueryFunctionSpec] = {spec.name: spec for spec in FUNCTION_SPECS}


# --- result type ---------------------------------------------------------------


@dataclass(frozen=True)
class NLQueryResult:
    status: str  # "ok" | "out_of_scope" | "error"
    question: str
    function: str | None = None
    parameters: dict[str, Any] | None = None
    data: Any | None = None
    message: str | None = None
    notes: list[str] = field(default_factory=list)


def _out_of_scope(question: str) -> NLQueryResult:
    return NLQueryResult(status="out_of_scope", question=question, message=OUT_OF_SCOPE_MESSAGE)


# --- prompt & parsing --------------------------------------------------------


def build_system_prompt() -> str:
    """Describe the fixed function list to the model. Built from the registry
    so the prompt can't drift from what actually dispatches."""
    lines = [
        "You route an HR analyst's question to exactly one predefined analytics "
        "function. You never write SQL, never invent functions, and never answer "
        "in prose.",
        "",
        "Reply with a single JSON object and nothing else:",
        '{"function": "<one of the names below>", "parameters": { ... }}',
        "",
        "If the question cannot be answered by one of these functions, reply with "
        '{"function": "none", "parameters": {}}.',
        "",
        "Functions:",
    ]
    for spec in FUNCTION_SPECS:
        lines.append(f"- {spec.name}: {spec.description}")
        for pname, pspec in spec.parameters.items():
            bounds = ""
            if pspec.enum:
                bounds = f" (one of: {', '.join(pspec.enum)})"
            elif pspec.minimum is not None or pspec.maximum is not None:
                bounds = f" (integer {pspec.minimum}-{pspec.maximum})"
            lines.append(f"    parameter {pname}{bounds}: {pspec.description}")
    return "\n".join(lines)


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        # ```json\n...\n```  or  ```\n...\n```
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.rstrip().endswith("```"):
            text = text.rstrip()[:-3]
    return text.strip()


def _extract_selection(raw_content: str) -> tuple[str, dict]:
    """Parse the model reply into (function_name, parameters). Raises
    SelectionParseError for anything that isn't the shape we asked for."""
    if not raw_content or not raw_content.strip():
        raise SelectionParseError("empty model reply")
    try:
        parsed = json.loads(_strip_code_fence(raw_content))
    except json.JSONDecodeError as exc:
        raise SelectionParseError(f"reply was not JSON: {exc}") from exc
    if not isinstance(parsed, dict) or not isinstance(parsed.get("function"), str):
        raise SelectionParseError("reply had no string 'function' field")

    params = parsed.get("parameters", {})
    if isinstance(params, str):
        try:
            params = json.loads(params)
        except json.JSONDecodeError:
            params = {}
    if not isinstance(params, dict):
        params = {}
    return parsed["function"], params


def _coerce_params(spec: QueryFunctionSpec, raw: dict) -> tuple[dict, list[str]]:
    """Validate/bound the model's parameters against the function's spec.
    Unknown keys are dropped; out-of-range or wrong-typed values fall back to
    the default. Returns (clean_params, human-readable notes)."""
    clean: dict[str, Any] = {}
    notes: list[str] = []

    for key in raw:
        if key not in spec.parameters:
            notes.append(f"ignored unrecognized parameter '{key}'")

    for name, pspec in spec.parameters.items():
        if name not in raw or raw[name] is None:
            if pspec.default is not None:
                clean[name] = pspec.default
            continue
        value = raw[name]

        if pspec.type == "string":
            if isinstance(value, str) and value.strip():
                clean[name] = value.strip()
            else:
                notes.append(f"ignored non-text value for '{name}'")

        elif pspec.type == "enum":
            match = next(
                (opt for opt in (pspec.enum or ()) if str(value).strip().lower() == opt.lower()),
                None,
            )
            if match is not None:
                clean[name] = match
            else:
                notes.append(f"ignored unknown '{name}' value {value!r}")

        elif pspec.type == "integer":
            try:
                number = int(value)
            except (TypeError, ValueError):
                notes.append(f"ignored non-numeric value for '{name}'")
                if pspec.default is not None:
                    clean[name] = pspec.default
                continue
            if pspec.minimum is not None and number < pspec.minimum:
                notes.append(f"raised '{name}' to the minimum of {pspec.minimum}")
                number = pspec.minimum
            if pspec.maximum is not None and number > pspec.maximum:
                notes.append(f"capped '{name}' at the maximum of {pspec.maximum}")
                number = pspec.maximum
            clean[name] = number

    return clean, notes


# --- the OpenRouter call (the one mocked seam) --------------------------------

ModelCaller = Callable[[str], str]


def default_model_caller(question: str) -> str:
    """Ask the allowlisted OpenRouter model to select a function. Returns the
    raw assistant message content (expected to be JSON).

    This is the production `model_caller`; the endpoint injects it via a
    dependency so tests can swap in a canned one.
    """
    api_key = (settings.openrouter_api_key or "").strip()
    if not api_key:
        raise OpenRouterNotConfiguredError(
            "OPENROUTER_API_KEY is not set — the natural-language query feature is disabled."
        )

    model = resolve_openrouter_model()  # hardcoded default, still through the guard
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": question},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "max_tokens": _MODEL_MAX_TOKENS,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(_MODEL_RETRY_ON_429 + 1):
        try:
            response = httpx.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
                timeout=_MODEL_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc

        if response.status_code == 429:
            if attempt < _MODEL_RETRY_ON_429:
                time.sleep(_MODEL_RETRY_BACKOFF_SECONDS)
                continue
            raise OpenRouterError("OpenRouter is rate-limited upstream; retry shortly.")

        try:
            response.raise_for_status()
            body = response.json()
            return body["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc

    raise OpenRouterError("OpenRouter is rate-limited upstream; retry shortly.")


# --- entry point -------------------------------------------------------------


def run_nl_query(
    session: Session,
    question: str,
    *,
    model_caller: ModelCaller | None = None,
) -> NLQueryResult:
    """Map `question` to one analytics function and run it.

    `model_caller` overrides the OpenRouter call for tests; production uses
    the module default.
    """
    question = (question or "").strip()
    if not question:
        return NLQueryResult(
            status="error", question=question, message="Please enter a question."
        )

    caller = model_caller or default_model_caller
    try:
        raw_reply = caller(question)
    except OpenRouterNotConfiguredError as exc:
        return NLQueryResult(status="error", question=question, message=str(exc))
    except OpenRouterError:
        return NLQueryResult(
            status="error",
            question=question,
            message="The language model could not be reached. Please try again shortly.",
        )

    try:
        function_name, raw_params = _extract_selection(raw_reply)
    except SelectionParseError:
        return _out_of_scope(question)

    spec = FUNCTIONS.get(function_name)
    if spec is None:
        return _out_of_scope(question)

    clean_params, notes = _coerce_params(spec, raw_params)
    data = spec.runner(session, clean_params)
    return NLQueryResult(
        status="ok",
        question=question,
        function=spec.name,
        parameters=clean_params,
        data=data,
        notes=notes,
    )