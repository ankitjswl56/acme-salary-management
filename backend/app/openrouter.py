"""OpenRouter access policy for the stretch NL-analytics-query feature.

This module is the hard, code-level guard CLAUDE.md's "OpenRouter guardrails"
section calls for. Two deliberate design choices:

1. The permitted-model set is a **hardcoded constant**, not a Settings field
   and not read from any env var or request payload. OpenRouter's
   free-vs-paid model routing has silently run accounts into a negative
   balance before; the only way this app can call a paid model is if someone
   edits this file in a commit. An operator cannot widen it by mistake.

2. There is no function here that forwards an arbitrary model string.
   `resolve_openrouter_model()` either returns the hardcoded default or a
   value it has just checked against the allowlist — anything else raises.

The allowlist was verified against https://openrouter.ai/api/v1/models on
2026-09-04. Note: the `meta-llama/llama-3.1-8b-instruct:free` id used as an
example in the early planning docs (CLAUDE.md, requirements.md) no longer
exists — OpenRouter delisted the free Meta Llama tier in Aug 2026 — so the
allowlist intentionally does not contain it.
"""

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Free-tier chat models that expose structured-output params, so the
# function-selection call can ask for JSON reliably. Keep this list short and
# every entry ending in ":free". All three were reachable on 2026-09-04, but
# the free tier shares an upstream pool across all OpenRouter users, so any
# one of them can return a transient upstream 429 at any time — the caller
# retries once, then surfaces a 503.
OPENROUTER_MODEL_ALLOWLIST: frozenset[str] = frozenset(
    {
        "nvidia/nemotron-3-super-120b-a12b:free",
        "google/gemma-4-31b-it:free",
        "z-ai/glm-5.2:free",
    }
)

# The single model the NL-query feature actually calls. Chosen because it was
# the one of the three not upstream-rate-limited during the 2026-09-04 smoke
# test and it selected the right function + params on every probe. Must be on
# the allowlist.
OPENROUTER_DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

# A paid model can only reach OpenRouter through this file, and only via a
# real code edit — fail loudly at import if the default ever drifts off the
# allowlist.
assert OPENROUTER_DEFAULT_MODEL in OPENROUTER_MODEL_ALLOWLIST
assert all(model_id.endswith(":free") for model_id in OPENROUTER_MODEL_ALLOWLIST)


class DisallowedModelError(ValueError):
    """Raised when code tries to call an OpenRouter model that is not on the
    hardcoded free-tier allowlist."""


def resolve_openrouter_model(requested: str | None = None) -> str:
    """Return the OpenRouter model id to call.

    ``None`` -> the hardcoded default. Any explicit value must already be on
    the allowlist, or this raises :class:`DisallowedModelError`. This is the
    only place a model id is chosen; callers never pass a raw string through
    to the HTTP layer.
    """
    if requested is None:
        return OPENROUTER_DEFAULT_MODEL
    if requested not in OPENROUTER_MODEL_ALLOWLIST:
        raise DisallowedModelError(
            f"Model {requested!r} is not on the OpenRouter free-tier allowlist; "
            f"permitted: {sorted(OPENROUTER_MODEL_ALLOWLIST)}"
        )
    return requested