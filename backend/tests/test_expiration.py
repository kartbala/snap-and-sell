"""Tests for listing expiration logic."""

import os
import tempfile
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from backend.database import init_db, get_connection
from backend import models


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


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


def _backdate_listing(db_path: str, lid: int, days_ago: int):
    """Set a listing's created_at to N days ago."""
    old_date = (datetime.now() - timedelta(days=days_ago)).isoformat()
    conn = get_connection(db_path)
    conn.execute(
        "UPDATE listings SET created_at = ?, updated_at = ? WHERE id = ?",
        (old_date, old_date, lid),
    )
    conn.commit()
    conn.close()


class TestExpirationLogic:
    def test_fresh_listing_not_expired(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="New", asking_price=100), db_path
        )
        models.batch_update_status([lid], "active", db_path)
        listing = models.get_listing(lid, db_path)
        assert listing.status == "active"

    def test_old_listing_still_in_db(self, db_path):
        """Listings older than 30 days still exist, just not on marketplace."""
        lid = models.create_listing(
            models.ListingCreate(title="Old", asking_price=100), db_path
        )
        models.batch_update_status([lid], "active", db_path)
        _backdate_listing(db_path, lid, 45)
        listing = models.get_listing(lid, db_path)
        assert listing is not None


class TestMarketplaceExpiration:
    def test_marketplace_excludes_expired_listings(self, client):
        """Listings older than 30 days don't appear on marketplace."""
        # Create and approve a listing
        resp = client.post("/api/listings", json={
            "title": "Old Item", "asking_price": 100,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        # Verify it's on marketplace
        assert len(client.get("/api/marketplace").json()) == 1

        # Backdate it
        db_path = os.environ["DB_PATH"]
        _backdate_listing(db_path, lid, 35)

        # Should be gone from marketplace
        assert len(client.get("/api/marketplace").json()) == 0

    def test_marketplace_includes_recent_listings(self, client):
        """Listings under 30 days old still appear."""
        resp = client.post("/api/listings", json={
            "title": "Recent", "asking_price": 100,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        db_path = os.environ["DB_PATH"]
        _backdate_listing(db_path, lid, 25)

        marketplace = client.get("/api/marketplace").json()
        assert len(marketplace) == 1

    def test_mix_of_fresh_and_expired(self, client):
        """Only fresh items show on marketplace."""
        db_path = os.environ["DB_PATH"]
        ids = []
        for i in range(4):
            resp = client.post("/api/listings", json={
                "title": f"Item {i}", "asking_price": 100,
            })
            ids.append(resp.json()["id"])
        client.post("/api/listings/batch-approve", json={"ids": ids})

        # Backdate first 2 past expiration
        _backdate_listing(db_path, ids[0], 40)
        _backdate_listing(db_path, ids[1], 31)

        marketplace = client.get("/api/marketplace").json()
        assert len(marketplace) == 2
        titles = {m["title"] for m in marketplace}
        assert "Item 2" in titles
        assert "Item 3" in titles

    def test_exactly_29_days_still_shows(self, client):
        """Listing at 29 days is still visible (within 30-day window)."""
        resp = client.post("/api/listings", json={
            "title": "Borderline", "asking_price": 100,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        db_path = os.environ["DB_PATH"]
        _backdate_listing(db_path, lid, 29)

        marketplace = client.get("/api/marketplace").json()
        assert len(marketplace) == 1

    def test_day_31_excluded(self, client):
        """Listing at 31 days is excluded."""
        resp = client.post("/api/listings", json={
            "title": "Expired", "asking_price": 100,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        db_path = os.environ["DB_PATH"]
        _backdate_listing(db_path, lid, 31)

        marketplace = client.get("/api/marketplace").json()
        assert len(marketplace) == 0

    def test_marketplace_response_includes_days_remaining(self, client):
        """Each marketplace listing includes days_remaining field."""
        resp = client.post("/api/listings", json={
            "title": "Fresh", "asking_price": 100,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        db_path = os.environ["DB_PATH"]
        _backdate_listing(db_path, lid, 10)

        marketplace = client.get("/api/marketplace").json()
        assert len(marketplace) == 1
        assert "days_remaining" in marketplace[0]
        # Allow for sub-day timing: 10 days ago means ~19-20 days remaining
        assert marketplace[0]["days_remaining"] in (19, 20)

    def test_seller_listings_still_show_expired(self, client):
        """Seller can still see expired listings via /api/listings."""
        resp = client.post("/api/listings", json={
            "title": "Old", "asking_price": 100,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        db_path = os.environ["DB_PATH"]
        _backdate_listing(db_path, lid, 45)

        # Seller endpoint still shows it
        listings = client.get("/api/listings?status=active").json()
        assert len(listings) == 1


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

    def test_accepted_offer_includes_meeting_spot(self, client):
        """When an offer is accepted, response includes a meeting spot."""
        resp = client.post("/api/listings", json={
            "title": "Widget", "asking_price": 100, "min_price": 70,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Alice",
            "buyer_phone": "202-555-1234", "offer_amount": 100,
        })
        data = resp.json()
        assert data["decision"] == "accepted"
        assert "meeting_spot" in data
        assert "name" in data["meeting_spot"]
        assert "address" in data["meeting_spot"]

    def test_rejected_offer_no_meeting_spot(self, client):
        """Rejected offers don't include meeting spots."""
        resp = client.post("/api/listings", json={
            "title": "Widget", "asking_price": 100, "min_price": 70,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Bob",
            "buyer_phone": "555-1111", "offer_amount": 30,
        })
        data = resp.json()
        assert data["decision"] == "rejected"
        assert "meeting_spot" not in data or data.get("meeting_spot") is None

    def test_pending_offer_no_meeting_spot(self, client):
        """Pending offers don't include meeting spots."""
        resp = client.post("/api/listings", json={
            "title": "No Min", "asking_price": 100,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Carol",
            "buyer_phone": "555-2222", "offer_amount": 80,
        })
        data = resp.json()
        assert data["decision"] == "pending"
        assert "meeting_spot" not in data or data.get("meeting_spot") is None
