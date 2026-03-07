"""Edge case and boundary tests for negotiation engine."""

import pytest
from backend.negotiation import evaluate_offer


class TestNegotiationBoundaries:
    def test_one_cent_above_asking(self):
        result = evaluate_offer(100.01, 100.0, 70.0)
        assert result.decision == "accepted"

    def test_one_cent_below_asking_above_min(self):
        result = evaluate_offer(99.99, 100.0, 70.0)
        assert result.decision == "accepted"

    def test_one_cent_below_min(self):
        result = evaluate_offer(69.99, 100.0, 70.0)
        assert result.decision == "rejected"

    def test_one_cent_above_min(self):
        result = evaluate_offer(70.01, 100.0, 70.0)
        assert result.decision == "accepted"

    def test_very_small_offer(self):
        result = evaluate_offer(0.01, 100.0, 70.0)
        assert result.decision == "rejected"

    def test_very_large_offer(self):
        result = evaluate_offer(999999.99, 100.0, 70.0)
        assert result.decision == "accepted"

    def test_asking_equals_min(self):
        """When asking == min, any offer at that price should accept."""
        result = evaluate_offer(100.0, 100.0, 100.0)
        assert result.decision == "accepted"

    def test_asking_equals_min_below(self):
        result = evaluate_offer(99.99, 100.0, 100.0)
        assert result.decision == "rejected"

    def test_min_greater_than_asking(self):
        """Edge case: min_price > asking_price (misconfigured)."""
        # Offer at asking should still be accepted
        result = evaluate_offer(50.0, 50.0, 100.0)
        assert result.decision == "accepted"
        # Offer above min should be accepted
        result = evaluate_offer(100.0, 50.0, 100.0)
        assert result.decision == "accepted"
        # Offer between asking and min — accepted because it's above asking
        result = evaluate_offer(75.0, 50.0, 100.0)
        assert result.decision == "accepted"
        # Offer below asking but above 0 — rejected (below both thresholds effectively)
        result = evaluate_offer(30.0, 50.0, 100.0)
        assert result.decision == "rejected"


class TestNegotiationMessages:
    def test_accepted_message_mentions_seller(self):
        result = evaluate_offer(100.0, 100.0, 70.0)
        assert "seller" in result.message.lower()

    def test_rejected_message_mentions_asking_price(self):
        result = evaluate_offer(50.0, 100.0, 70.0)
        assert "100" in result.message

    def test_pending_message_mentions_review(self):
        result = evaluate_offer(80.0, 100.0, None)
        assert "review" in result.message.lower()

    def test_invalid_message_mentions_invalid(self):
        result = evaluate_offer(0.0, 100.0, 70.0)
        assert "invalid" in result.message.lower()


class TestNegotiationNoAskingPrice:
    def test_no_asking_no_min_pending(self):
        """Both prices None — should be pending."""
        result = evaluate_offer(50.0, None, None)
        assert result.decision == "pending"

    def test_no_asking_with_min_below(self):
        result = evaluate_offer(50.0, None, 70.0)
        assert result.decision == "rejected"

    def test_no_asking_with_min_above(self):
        result = evaluate_offer(80.0, None, 70.0)
        assert result.decision == "accepted"


class TestNegotiationReturnTypes:
    def test_result_always_has_decision(self):
        for offer in [0, -1, 50, 70, 100, 150]:
            result = evaluate_offer(float(offer), 100.0, 70.0)
            assert result.decision in ("accepted", "rejected", "pending")

    def test_result_always_has_message(self):
        for offer in [0, -1, 50, 70, 100, 150]:
            result = evaluate_offer(float(offer), 100.0, 70.0)
            assert isinstance(result.message, str)
            assert len(result.message) > 0

    def test_counter_amount_always_none_for_mvp(self):
        """MVP doesn't implement counter-offers."""
        for offer in [0, 50, 70, 100, 150]:
            result = evaluate_offer(float(offer), 100.0, 70.0)
            assert result.counter_amount is None
