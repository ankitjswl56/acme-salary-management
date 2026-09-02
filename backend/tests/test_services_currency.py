import pytest

from app.services.currency import (
    InvalidAmountError,
    UnsupportedCurrencyError,
    normalize_to_usd,
)


def test_normalize_to_usd_uses_fixed_fx_rate():
    amount_usd, fx_rate = normalize_to_usd(1000, "GBP")

    assert fx_rate == pytest.approx(1.27)
    assert amount_usd == pytest.approx(1270.0)


def test_normalize_to_usd_usd_is_identity():
    amount_usd, fx_rate = normalize_to_usd(50000, "USD")

    assert fx_rate == 1.0
    assert amount_usd == 50000.0


def test_normalize_to_usd_rejects_unsupported_currency():
    with pytest.raises(UnsupportedCurrencyError):
        normalize_to_usd(1000, "XYZ")


def test_normalize_to_usd_rejects_negative_amount():
    with pytest.raises(InvalidAmountError):
        normalize_to_usd(-1, "USD")


def test_normalize_to_usd_never_does_a_live_lookup_for_the_same_currency_twice():
    """FX rate must be a fixed reference value, not something that can drift
    between two calls in the same process (i.e. not a live/runtime lookup)."""
    first_call = normalize_to_usd(1000, "INR")
    second_call = normalize_to_usd(1000, "INR")

    assert first_call == second_call