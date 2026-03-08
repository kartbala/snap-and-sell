"""Tests for notification API endpoints."""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from backend.database import init_db


@pytest.fixture
def client():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(db_path)
    os.environ["DB_PATH"] = db_path
    from backend.api import app, _get_db_path
    _get_db_path.cache_clear()
    with TestClient(app) as c:
        yield c
    os.unlink(db_path)


def _make_active_listing(client, title="Widget", asking=100.0, min_price=70.0):
    resp = client.post("/api/listings", json={
        "title": title, "asking_price": asking, "min_price": min_price,
    })
    lid = resp.json()["id"]
    client.post("/api/listings/batch-approve", json={"ids": [lid]})
    return lid


class TestOfferCreatesNotification:
    def test_offer_creates_notification(self, client):
        lid = _make_active_listing(client)
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Alice",
            "buyer_phone": "202-555-1234", "offer_amount": 100,
        })
        resp = client.get("/api/notifications?sent=false")
        assert resp.status_code == 200
        notifs = resp.json()
        assert len(notifs) == 1
        assert notifs[0]["listing_id"] == lid
        assert notifs[0]["type"] == "new_offer"
        assert notifs[0]["sent"] is False

    def test_multiple_offers_create_multiple_notifications(self, client):
        lid = _make_active_listing(client)
        for name in ["Alice", "Bob", "Carol"]:
            client.post("/api/offers", json={
                "listing_id": lid, "buyer_name": name,
                "buyer_phone": "555-0000", "offer_amount": 80,
            })
        resp = client.get("/api/notifications?sent=false")
        assert len(resp.json()) == 3

    def test_rejected_offer_still_creates_notification(self, client):
        lid = _make_active_listing(client)
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Lowball",
            "buyer_phone": "555", "offer_amount": 10,
        })
        resp = client.get("/api/notifications?sent=false")
        assert len(resp.json()) == 1


class TestNotificationEndpoints:
    def test_list_pending(self, client):
        lid = _make_active_listing(client)
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "X",
            "buyer_phone": "555", "offer_amount": 80,
        })
        resp = client.get("/api/notifications?sent=false")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_all(self, client):
        resp = client.get("/api/notifications")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_mark_sent(self, client):
        lid = _make_active_listing(client)
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "X",
            "buyer_phone": "555", "offer_amount": 80,
        })
        notifs = client.get("/api/notifications?sent=false").json()
        nid = notifs[0]["id"]

        resp = client.put(f"/api/notifications/{nid}")
        assert resp.status_code == 200

        # Now pending is empty
        assert len(client.get("/api/notifications?sent=false").json()) == 0
        # But all shows 1 (sent)
        assert len(client.get("/api/notifications").json()) == 1

    def test_mark_sent_nonexistent(self, client):
        resp = client.put("/api/notifications/999")
        assert resp.status_code == 404

    def test_notification_includes_context(self, client):
        """Notification response includes listing title and offer details."""
        lid = _make_active_listing(client, title="Fancy Chair", asking=500)
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Alice",
            "buyer_phone": "202-555-1234", "offer_amount": 400,
        })
        notifs = client.get("/api/notifications?sent=false").json()
        n = notifs[0]
        assert n["listing_title"] == "Fancy Chair"
        assert n["buyer_name"] == "Alice"
        assert n["offer_amount"] == 400.0
        assert "decision" in n


class TestNotificationCount:
    def test_dashboard_notification_count(self, client):
        """GET /api/notifications/count returns unsent count."""
        lid = _make_active_listing(client)
        for i in range(3):
            client.post("/api/offers", json={
                "listing_id": lid, "buyer_name": f"Buyer{i}",
                "buyer_phone": "555", "offer_amount": 80,
            })
        resp = client.get("/api/notifications/count")
        assert resp.status_code == 200
        assert resp.json()["unsent"] == 3
