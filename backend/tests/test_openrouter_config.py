"""The OpenRouter free-tier allowlist guard (CLAUDE.md § OpenRouter guardrails).

The point of these tests is that the guard rejects at the code level, not by
convention: a model that isn't explicitly listed cannot be called, and the
list can only ever contain free models.
"""

import pytest

from app.openrouter import (
    OPENROUTER_DEFAULT_MODEL,
    OPENROUTER_MODEL_ALLOWLIST,
    DisallowedModelError,
    resolve_openrouter_model,
)


def test_default_model_is_on_the_allowlist():
    assert OPENROUTER_DEFAULT_MODEL in OPENROUTER_MODEL_ALLOWLIST


def test_every_allowlisted_model_is_a_free_tier_id():
    # The negative-balance incident this guard exists to prevent came from a
    # paid model slipping through, so the invariant is: nothing here bills.
    assert OPENROUTER_MODEL_ALLOWLIST, "allowlist must not be empty"
    for model_id in OPENROUTER_MODEL_ALLOWLIST:
        assert model_id.endswith(":free"), model_id


def test_resolve_returns_default_when_nothing_requested():
    assert resolve_openrouter_model(None) == OPENROUTER_DEFAULT_MODEL
    assert resolve_openrouter_model() == OPENROUTER_DEFAULT_MODEL


def test_resolve_passes_through_an_allowlisted_model():
    a_listed_model = next(iter(OPENROUTER_MODEL_ALLOWLIST))
    assert resolve_openrouter_model(a_listed_model) == a_listed_model


def test_resolve_rejects_a_paid_model():
    with pytest.raises(DisallowedModelError):
        resolve_openrouter_model("openai/gpt-4o")


def test_resolve_rejects_an_unpinned_or_auto_routed_model():
    for model_id in ("openrouter/auto", "openrouter/free", ""):
        with pytest.raises(DisallowedModelError):
            resolve_openrouter_model(model_id)


def test_resolve_rejects_the_stale_planning_doc_example():
    # CLAUDE.md / requirements.md still cite this id as the example; OpenRouter
    # delisted the free Meta Llama tier in Aug 2026. If someone re-adds it by
    # copy-paste, this fails — the allowlist is not "anything ending in :free".
    with pytest.raises(DisallowedModelError):
        resolve_openrouter_model("meta-llama/llama-3.1-8b-instruct:free")