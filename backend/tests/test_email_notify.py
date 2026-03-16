"""Tests for email notification composition."""
import pytest
from backend.email_notify import compose_seller_notification, compose_buyer_acceptance


def test_seller_notification_contains_item_title():
    email = compose_seller_notification(
        listing_title="IKEA KALLAX",
        buyer_name="Jane",
        offer_amount=80.0,
        decision="accepted",
        dashboard_url="https://sell.example.com/dashboard",
    )
    assert "IKEA KALLAX" in email["subject"]
    assert "Jane" in email["body"]
    assert "$80.00" in email["body"]
    assert "accepted" in email["body"].lower()


def test_seller_notification_has_correct_to():
    email = compose_seller_notification(
        listing_title="Chair",
        buyer_name="Bob",
        offer_amount=50.0,
        decision="rejected",
        notification_email="karthik@balasubramanian.us",
    )
    assert email["to"] == "karthik@balasubramanian.us"


def test_buyer_acceptance_meeting_spot():
    email = compose_buyer_acceptance(
        listing_title="Desk",
        offer_amount=120.0,
        buyer_email="buyer@example.com",
        pickup_type="meeting_spot",
        pickup_details="Tenleytown Metro Station",
        contact_number="+1-202-684-6252",
    )
    assert email["to"] == "buyer@example.com"
    assert "Desk" in email["subject"]
    assert "Tenleytown" in email["body"]
    assert "+1-202-684-6252" in email["body"]


def test_buyer_acceptance_home_pickup():
    email = compose_buyer_acceptance(
        listing_title="Couch",
        offer_amount=200.0,
        buyer_email="buyer@example.com",
        pickup_type="home",
        pickup_details="123 Main St, Washington DC",
        contact_number="+1-202-684-6252",
    )
    assert "123 Main St" in email["body"]
