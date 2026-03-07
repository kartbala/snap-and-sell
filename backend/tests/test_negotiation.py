import pytest
from backend.negotiation import evaluate_offer, NegotiationResult


class TestNegotiation:
    def test_at_asking_price(self):
        result = evaluate_offer(100.0, 100.0, 70.0)
        assert result.decision == "accepted"

    def test_above_asking_price(self):
        result = evaluate_offer(120.0, 100.0, 70.0)
        assert result.decision == "accepted"

    def test_at_min_price(self):
        result = evaluate_offer(70.0, 100.0, 70.0)
        assert result.decision == "accepted"

    def test_between_min_and_asking(self):
        result = evaluate_offer(85.0, 100.0, 70.0)
        assert result.decision == "accepted"

    def test_below_min_price(self):
        result = evaluate_offer(50.0, 100.0, 70.0)
        assert result.decision == "rejected"
        assert "100" in result.message  # Should mention asking price

    def test_zero_offer(self):
        result = evaluate_offer(0.0, 100.0, 70.0)
        assert result.decision == "rejected"

    def test_negative_offer(self):
        result = evaluate_offer(-10.0, 100.0, 70.0)
        assert result.decision == "rejected"

    def test_no_min_price_pending(self):
        result = evaluate_offer(80.0, 100.0, None)
        assert result.decision == "pending"

    def test_no_min_price_at_asking_accepted(self):
        result = evaluate_offer(100.0, 100.0, None)
        assert result.decision == "accepted"

    def test_no_min_price_above_asking_accepted(self):
        result = evaluate_offer(110.0, 100.0, None)
        assert result.decision == "accepted"

    def test_result_has_message(self):
        result = evaluate_offer(100.0, 100.0, 70.0)
        assert isinstance(result.message, str)
        assert len(result.message) > 0

    def test_rejected_has_no_counter(self):
        result = evaluate_offer(50.0, 100.0, 70.0)
        assert result.counter_amount is None

    def test_pending_has_no_counter(self):
        result = evaluate_offer(80.0, 100.0, None)
        assert result.counter_amount is None
