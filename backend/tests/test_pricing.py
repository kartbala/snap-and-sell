"""Tests for countdown pricing engine."""
import pytest
from datetime import date, timedelta
from backend.pricing import compute_current_price


class TestHoldStrategy:
    def test_hold_never_drops(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="hold",
            deadline=date.today() + timedelta(days=1),
        )
        assert result == 100.0

    def test_hold_even_past_deadline(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="hold",
            deadline=date.today() - timedelta(days=5),
        )
        assert result == 100.0


class TestAggressiveStrategy:
    def test_4_plus_weeks_no_discount(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=30),
        )
        assert result == 100.0

    def test_3_weeks_10_percent_off(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=25),
        )
        assert result == 90.0

    def test_2_weeks_20_percent_off(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=18),
        )
        assert result == 80.0

    def test_1_week_35_percent_off(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=10),
        )
        assert result == 65.0

    def test_last_3_days_50_percent_off(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=2),
        )
        assert result == 50.0

    def test_never_below_min_price(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=70.0,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=2),
        )
        assert result == 70.0  # 50% off = 50, but min_price = 70

    def test_no_min_price_drops_fully(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=None,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=2),
        )
        assert result == 50.0


class TestFireSaleStrategy:
    def test_14_days_out_no_discount(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=None,
            pricing_strategy="fire_sale",
            deadline=date.today() + timedelta(days=15),
        )
        assert result == 100.0

    def test_13_days_out_5_percent_off(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=None,
            pricing_strategy="fire_sale",
            deadline=date.today() + timedelta(days=13),
        )
        assert result == 95.0

    def test_7_days_out_35_percent_off(self):
        # 14 - 7 = 7 days into fire sale, 7 * 5% = 35%
        result = compute_current_price(
            asking_price=100.0,
            min_price=None,
            pricing_strategy="fire_sale",
            deadline=date.today() + timedelta(days=7),
        )
        assert result == 65.0

    def test_max_70_percent_off(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=None,
            pricing_strategy="fire_sale",
            deadline=date.today(),
        )
        assert result == 30.0  # 14 * 5% = 70% off, so 30

    def test_respects_min_price(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=80.0,
            pricing_strategy="fire_sale",
            deadline=date.today() + timedelta(days=7),
        )
        assert result == 80.0  # 35% off = 65, but min = 80


class TestEdgeCases:
    def test_no_asking_price_returns_none(self):
        result = compute_current_price(
            asking_price=None,
            min_price=None,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=10),
        )
        assert result is None

    def test_past_deadline_uses_max_discount(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=None,
            pricing_strategy="aggressive",
            deadline=date.today() - timedelta(days=5),
        )
        assert result == 50.0  # Max aggressive discount

    def test_unknown_strategy_treated_as_hold(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="unknown",
            deadline=date.today() + timedelta(days=2),
        )
        assert result == 100.0
