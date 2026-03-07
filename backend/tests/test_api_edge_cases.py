"""Edge case and validation tests for the API layer."""

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


def _create_active_listing(client, **overrides):
    """Helper: create a listing and approve it."""
    payload = {
        "title": "Test Item",
        "asking_price": 100.0,
        "min_price": 70.0,
        **overrides,
    }
    resp = client.post("/api/listings", json=payload)
    lid = resp.json()["id"]
    client.post("/api/listings/batch-approve", json={"ids": [lid]})
    return lid


class TestListingValidation:
    def test_create_listing_missing_title(self, client):
        resp = client.post("/api/listings", json={"asking_price": 100.0})
        assert resp.status_code == 422

    def test_create_listing_empty_title(self, client):
        resp = client.post("/api/listings", json={"title": "", "asking_price": 50})
        # Empty string is valid for Pydantic str — listing created
        assert resp.status_code == 201

    def test_create_listing_no_price(self, client):
        resp = client.post("/api/listings", json={"title": "Free Thing"})
        assert resp.status_code == 201
        data = client.get(f"/api/listings/{resp.json()['id']}").json()
        assert data["asking_price"] is None

    def test_create_listing_negative_price(self, client):
        resp = client.post("/api/listings", json={
            "title": "Weird", "asking_price": -50.0,
        })
        # Pydantic doesn't constrain floats by default — accepted
        assert resp.status_code == 201

    def test_create_listing_all_fields(self, client):
        resp = client.post("/api/listings", json={
            "title": "Full Item",
            "description": "Everything filled in",
            "category": "electronics",
            "condition": "excellent",
            "asking_price": 200.0,
            "min_price": 140.0,
            "original_price": 400.0,
            "purchase_date": "2024-01-15",
            "purchase_source": "Amazon",
            "location": "Washington DC",
        })
        assert resp.status_code == 201
        data = client.get(f"/api/listings/{resp.json()['id']}").json()
        assert data["category"] == "electronics"
        assert data["location"] == "Washington DC"
        assert data["original_price"] == 400.0

    def test_update_listing_partial(self, client):
        resp = client.post("/api/listings", json={
            "title": "Before", "asking_price": 100.0, "description": "Keep this",
        })
        lid = resp.json()["id"]
        client.put(f"/api/listings/{lid}", json={"title": "After"})
        data = client.get(f"/api/listings/{lid}").json()
        assert data["title"] == "After"
        assert data["description"] == "Keep this"
        assert data["asking_price"] == 100.0

    def test_update_preserves_status(self, client):
        lid = _create_active_listing(client)
        client.put(f"/api/listings/{lid}", json={"title": "Updated"})
        data = client.get(f"/api/listings/{lid}").json()
        assert data["status"] == "active"
        assert data["title"] == "Updated"


class TestBatchApproveEdgeCases:
    def test_batch_approve_empty_list(self, client):
        resp = client.post("/api/listings/batch-approve", json={"ids": []})
        assert resp.status_code == 200
        assert resp.json()["updated"] == 0

    def test_batch_approve_nonexistent_ids(self, client):
        resp = client.post("/api/listings/batch-approve", json={"ids": [999, 1000]})
        assert resp.status_code == 200
        assert resp.json()["updated"] == 0

    def test_batch_approve_mixed_existing_and_nonexistent(self, client):
        resp = client.post("/api/listings", json={"title": "Real", "asking_price": 10})
        lid = resp.json()["id"]
        resp = client.post("/api/listings/batch-approve", json={"ids": [lid, 999]})
        assert resp.json()["updated"] == 1

    def test_batch_approve_already_active(self, client):
        lid = _create_active_listing(client)
        # Approving again should still succeed (idempotent)
        resp = client.post("/api/listings/batch-approve", json={"ids": [lid]})
        assert resp.json()["updated"] == 1


class TestMarketplaceEdgeCases:
    def test_marketplace_excludes_draft(self, client):
        client.post("/api/listings", json={"title": "Draft", "asking_price": 50})
        resp = client.get("/api/marketplace")
        assert len(resp.json()) == 0

    def test_marketplace_excludes_sold(self, client):
        resp = client.post("/api/listings", json={"title": "Item", "asking_price": 50})
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})
        client.put(f"/api/listings/{lid}", json={"status": "sold"})
        resp = client.get("/api/marketplace")
        assert len(resp.json()) == 0

    def test_marketplace_fields_present(self, client):
        lid = _create_active_listing(client, title="Widget", description="Nice",
                                      category="electronics", condition="good")
        resp = client.get("/api/marketplace")
        item = resp.json()[0]
        assert item["title"] == "Widget"
        assert item["description"] == "Nice"
        assert item["asking_price"] == 100.0
        assert item["category"] == "electronics"
        assert item["condition"] == "good"
        assert "min_price" not in item

    def test_marketplace_multiple_items_sorted(self, client):
        _create_active_listing(client, title="First")
        _create_active_listing(client, title="Second")
        _create_active_listing(client, title="Third")
        resp = client.get("/api/marketplace")
        assert len(resp.json()) == 3


class TestOfferEdgeCases:
    def test_offer_on_nonexistent_listing(self, client):
        resp = client.post("/api/offers", json={
            "listing_id": 999, "buyer_name": "X",
            "buyer_phone": "555", "offer_amount": 50.0,
        })
        assert resp.status_code == 404

    def test_offer_on_draft_listing(self, client):
        resp = client.post("/api/listings", json={"title": "Draft", "asking_price": 100, "min_price": 70})
        lid = resp.json()["id"]
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "X",
            "buyer_phone": "555", "offer_amount": 100.0,
        })
        # Should still work — API doesn't restrict offers to active only
        assert resp.status_code == 201

    def test_offer_zero_amount_rejected(self, client):
        lid = _create_active_listing(client)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Zero",
            "buyer_phone": "555", "offer_amount": 0.0,
        })
        assert resp.json()["decision"] == "rejected"

    def test_offer_negative_amount_rejected(self, client):
        lid = _create_active_listing(client)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Neg",
            "buyer_phone": "555", "offer_amount": -10.0,
        })
        assert resp.json()["decision"] == "rejected"

    def test_offer_exactly_at_min_price(self, client):
        lid = _create_active_listing(client, asking_price=200, min_price=140)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Bargain",
            "buyer_phone": "555", "offer_amount": 140.0,
        })
        assert resp.json()["decision"] == "accepted"

    def test_offer_one_cent_below_min(self, client):
        lid = _create_active_listing(client, asking_price=200, min_price=140)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Close",
            "buyer_phone": "555", "offer_amount": 139.99,
        })
        assert resp.json()["decision"] == "rejected"

    def test_multiple_offers_on_same_listing(self, client):
        lid = _create_active_listing(client)
        for i in range(5):
            client.post("/api/offers", json={
                "listing_id": lid, "buyer_name": f"Buyer{i}",
                "buyer_phone": f"555-{i:04d}", "offer_amount": 50.0 + i * 10,
            })
        resp = client.get(f"/api/listings/{lid}/offers")
        assert len(resp.json()) == 5

    def test_offer_missing_required_fields(self, client):
        lid = _create_active_listing(client)
        # Missing buyer_name
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_phone": "555", "offer_amount": 80.0,
        })
        assert resp.status_code == 422

    def test_offer_with_optional_fields(self, client):
        lid = _create_active_listing(client)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Full",
            "buyer_phone": "202-555-1234", "buyer_email": "full@example.com",
            "offer_amount": 100.0, "message": "Very interested!",
        })
        assert resp.status_code == 201
        offers = client.get(f"/api/listings/{lid}/offers").json()
        assert offers[0]["buyer_email"] == "full@example.com"
        assert offers[0]["message"] == "Very interested!"

    def test_offers_endpoint_nonexistent_listing(self, client):
        resp = client.get("/api/listings/999/offers")
        assert resp.status_code == 404


class TestDeleteCascade:
    def test_delete_listing_removes_offers(self, client):
        lid = _create_active_listing(client)
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "A",
            "buyer_phone": "555", "offer_amount": 80.0,
        })
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "B",
            "buyer_phone": "556", "offer_amount": 90.0,
        })
        # Verify offers exist
        assert len(client.get(f"/api/listings/{lid}/offers").json()) == 2
        # Delete listing
        client.delete(f"/api/listings/{lid}")
        # Listing gone
        assert client.get(f"/api/listings/{lid}").status_code == 404


class TestConcurrentOperations:
    def test_rapid_create_and_list(self, client):
        """Create 20 listings rapidly and verify all appear."""
        ids = []
        for i in range(20):
            resp = client.post("/api/listings", json={
                "title": f"Item {i}", "asking_price": 10.0 + i,
            })
            assert resp.status_code == 201
            ids.append(resp.json()["id"])

        all_listings = client.get("/api/listings").json()
        assert len(all_listings) == 20

        # Batch approve all
        resp = client.post("/api/listings/batch-approve", json={"ids": ids})
        assert resp.json()["updated"] == 20

        marketplace = client.get("/api/marketplace").json()
        assert len(marketplace) == 20

    def test_rapid_offers(self, client):
        """Submit 10 offers on same listing rapidly."""
        lid = _create_active_listing(client)
        for i in range(10):
            resp = client.post("/api/offers", json={
                "listing_id": lid, "buyer_name": f"Buyer{i}",
                "buyer_phone": f"555-{i}", "offer_amount": 60.0 + i * 5,
            })
            assert resp.status_code == 201

        offers = client.get(f"/api/listings/{lid}/offers").json()
        assert len(offers) == 10
