"""Countdown pricing engine for liquidation deadlines."""
from __future__ import annotations
from datetime import date


def compute_current_price(
    asking_price: float | None,
    min_price: float | None,
    pricing_strategy: str,
    deadline: date,
) -> float | None:
    """Compute the current discounted price based on strategy and deadline.

    Returns None if asking_price is None.
    Never drops below min_price (if set).
    """
    if asking_price is None:
        return None

    days_left = (deadline - date.today()).days

    if pricing_strategy == "aggressive":
        discount = _aggressive_discount(days_left)
    elif pricing_strategy == "fire_sale":
        discount = _fire_sale_discount(days_left)
    else:
        # "hold" or unknown — no discount
        discount = 0.0

    discounted = asking_price * (1 - discount)

    if min_price is not None:
        discounted = max(discounted, min_price)

    return round(discounted, 2)


def _aggressive_discount(days_left: int) -> float:
    """Stepped discount schedule."""
    if days_left >= 28:
        return 0.0
    if days_left >= 21:
        return 0.10
    if days_left >= 14:
        return 0.20
    if days_left >= 7:
        return 0.35
    return 0.50


def _fire_sale_discount(days_left: int) -> float:
    """5% per day for last 14 days, max 70%."""
    if days_left >= 14:
        return 0.0
    days_into_sale = 14 - max(days_left, 0)
    return min(days_into_sale * 0.05, 0.70)
