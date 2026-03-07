from __future__ import annotations
from dataclasses import dataclass


@dataclass
class NegotiationResult:
    decision: str  # "accepted", "rejected", "pending"
    message: str
    counter_amount: float | None = None


def evaluate_offer(
    offer: float,
    asking_price: float | None,
    min_price: float | None,
) -> NegotiationResult:
    if offer <= 0:
        return NegotiationResult(
            decision="rejected",
            message="Invalid offer amount.",
        )

    if asking_price is not None and offer >= asking_price:
        return NegotiationResult(
            decision="accepted",
            message="Offer accepted! The seller will contact you shortly.",
        )

    if min_price is not None and offer >= min_price:
        return NegotiationResult(
            decision="accepted",
            message="Offer accepted! The seller will contact you shortly.",
        )

    if min_price is None:
        return NegotiationResult(
            decision="pending",
            message="Your offer has been submitted for review. The seller will respond soon.",
        )

    return NegotiationResult(
        decision="rejected",
        message=f"Offer too low. The asking price is ${asking_price:,.2f}.",
    )
