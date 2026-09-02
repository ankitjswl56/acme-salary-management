"""Currency normalization for SalaryRecord creation.

FX rates are fixed reference values (see app/reference_data.py), never a
live/runtime lookup, so historical amount_usd_snapshot figures stay
accurate regardless of how exchange rates move after the fact.
"""

from app.reference_data import COUNTRIES

FX_RATE_BY_CURRENCY: dict[str, float] = {country.currency: country.fx_rate_to_usd for country in COUNTRIES}

SUPPORTED_CURRENCIES: frozenset[str] = frozenset(FX_RATE_BY_CURRENCY)


class UnsupportedCurrencyError(ValueError):
    pass


class InvalidAmountError(ValueError):
    pass


def normalize_to_usd(amount: float, currency: str) -> tuple[float, float]:
    """Returns (amount_usd_snapshot, fx_rate_to_usd) for a given local amount.

    Raises UnsupportedCurrencyError / InvalidAmountError so callers (API
    routes) can turn these into 4xx responses instead of a raw 500.
    """
    if amount < 0:
        raise InvalidAmountError(f"Salary amount must be non-negative, got {amount}")

    fx_rate = FX_RATE_BY_CURRENCY.get(currency)
    if fx_rate is None:
        raise UnsupportedCurrencyError(
            f"Unsupported currency {currency!r}; supported: {sorted(SUPPORTED_CURRENCIES)}"
        )

    return round(amount * fx_rate, 2), fx_rate
