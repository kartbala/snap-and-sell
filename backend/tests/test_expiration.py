"""Tests for deadline-based marketplace filtering and pricing."""
import os
import tempfile
import pytest
from datetime import date, timedelta
from backend.database import init_db
from backend.models import ListingCreate, create_listing, update_listing, ListingUpdate


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


@pytest.fixture
def client(db_path):
    os.environ["DB_PATH"] = db_path
    from backend.api import app, _get_db_path
    _get_db_path.cache_clear()
    from fastapi.testclient import TestClient
    with TestClient(app) as c:
        yield c


def _create_listing(db_path, deadline, status="active", asking_price=100.0, min_price=70.0, pricing_strategy="aggressive"):
    lid = create_listing(
        ListingCreate(title="Test Item", asking_price=asking_price, min_price=min_price),
        db_path,
    )
    update_listing(lid, ListingUpdate(status=status, deadline=deadline, pricing_strategy=pricing_strategy), db_path)
    return lid


class TestDeadlineFiltering:
    def test_active_before_deadline_shows_in_marketplace(self, client, db_path):
        deadline = (date.today() + timedelta(days=30)).isoformat()
        _create_listing(db_path, deadline)
        res = client.get("/api/marketplace")
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_past_deadline_hidden_from_marketplace(self, client, db_path):
        deadline = (date.today() - timedelta(days=1)).isoformat()
        _create_listing(db_path, deadline)
        res = client.get("/api/marketplace")
        assert res.status_code == 200
        assert len(res.json()) == 0

    def test_draft_not_in_marketplace(self, client, db_path):
        deadline = (date.today() + timedelta(days=30)).isoformat()
        _create_listing(db_path, deadline, status="draft")
        res = client.get("/api/marketplace")
        assert len(res.json()) == 0

    def test_days_remaining_computed(self, client, db_path):
        deadline = (date.today() + timedelta(days=10)).isoformat()
        _create_listing(db_path, deadline)
        res = client.get("/api/marketplace")
        item = res.json()[0]
        assert item["days_remaining"] == 10

    def test_seller_listings_still_show_past_deadline(self, client, db_path):
        """Seller can still see past-deadline listings via /api/listings."""
        deadline = (date.today() - timedelta(days=5)).isoformat()
        _create_listing(db_path, deadline)
        listings = client.get("/api/listings?status=active").json()
        assert len(listings) == 1

    def test_mix_of_valid_and_expired_deadlines(self, client, db_path):
        future = (date.today() + timedelta(days=30)).isoformat()
        past = (date.today() - timedelta(days=1)).isoformat()
        _create_listing(db_path, future)
        _create_listing(db_path, past)
        _create_listing(db_path, future)
        marketplace = client.get("/api/marketplace").json()
        assert len(marketplace) == 2


class TestCurrentPriceInMarketplace:
    def test_current_price_included(self, client, db_path):
        deadline = (date.today() + timedelta(days=30)).isoformat()
        _create_listing(db_path, deadline)
        res = client.get("/api/marketplace")
        item = res.json()[0]
        assert "current_price" in item

    def test_current_price_no_discount_far_deadline(self, client, db_path):
        deadline = (date.today() + timedelta(days=30)).isoformat()
        _create_listing(db_path, deadline, asking_price=100.0)
        item = client.get("/api/marketplace").json()[0]
        assert item["current_price"] == 100.0

    def test_current_price_discounted_near_deadline(self, client, db_path):
        deadline = (date.today() + timedelta(days=10)).isoformat()
        _create_listing(db_path, deadline, asking_price=100.0, min_price=50.0)
        item = client.get("/api/marketplace").json()[0]
        assert item["current_price"] == 65.0  # aggressive, 7-13 days = 35% off

    def test_hold_strategy_no_discount(self, client, db_path):
        deadline = (date.today() + timedelta(days=2)).isoformat()
        _create_listing(db_path, deadline, pricing_strategy="hold")
        item = client.get("/api/marketplace").json()[0]
        assert item["current_price"] == 100.0

    def test_min_price_not_exposed(self, client, db_path):
        deadline = (date.today() + timedelta(days=30)).isoformat()
        _create_listing(db_path, deadline)
        item = client.get("/api/marketplace").json()[0]
        assert "min_price" not in item

    def test_original_asking_price_included(self, client, db_path):
        deadline = (date.today() + timedelta(days=10)).isoformat()
        _create_listing(db_path, deadline, asking_price=100.0)
        item = client.get("/api/marketplace").json()[0]
        assert item["asking_price"] == 100.0  # original preserved


class TestMeetingSpotsAPI:
    def test_get_meeting_spots(self, client):
        resp = client.get("/api/meeting-spots")
        assert resp.status_code == 200
        spots = resp.json()
        assert len(spots) > 0
        assert "name" in spots[0]
        assert "address" in spots[0]

    def test_meeting_spots_have_types(self, client):
        resp = client.get("/api/meeting-spots")
        spots = resp.json()
        types = {s["type"] for s in spots}
        assert "police" in types

    def test_accepted_offer_includes_meeting_spot(self, client, db_path):
        """When an offer is accepted, response includes a meeting spot."""
        deadline = (date.today() + timedelta(days=30)).isoformat()
        lid = _create_listing(db_path, deadline, asking_price=100.0, min_price=70.0)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Alice",
            "buyer_phone": "202-555-1234", "offer_amount": 100.0,
        })
        data = resp.json()
        assert data["decision"] == "accepted"
        assert "meeting_spot" in data
        assert "name" in data["meeting_spot"]
        assert "address" in data["meeting_spot"]

    def test_rejected_offer_no_meeting_spot(self, client, db_path):
        """Rejected offers don't include meeting spots."""
        deadline = (date.today() + timedelta(days=30)).isoformat()
        lid = _create_listing(db_path, deadline, asking_price=100.0, min_price=70.0)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Bob",
            "buyer_phone": "555-1111", "offer_amount": 30.0,
        })
        data = resp.json()
        assert data["decision"] == "rejected"
        assert "meeting_spot" not in data or data.get("meeting_spot") is None

    def test_pending_offer_no_meeting_spot(self, client, db_path):
        """Pending offers don't include meeting spots."""
        deadline = (date.today() + timedelta(days=30)).isoformat()
        lid = _create_listing(db_path, deadline, asking_price=100.0, min_price=None)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Carol",
            "buyer_phone": "555-2222", "offer_amount": 80.0,
        })
        data = resp.json()
        assert data["decision"] == "pending"
        assert "meeting_spot" not in data or data.get("meeting_spot") is None
