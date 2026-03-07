"""Full lifecycle and payload validation tests for the API."""

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


class TestFullLifecycle:
    def test_draft_approve_offer_accept(self, client):
        """Happy path: create draft -> approve -> offer at asking -> accepted."""
        # Create
        resp = client.post("/api/listings", json={
            "title": "Widget", "asking_price": 100.0, "min_price": 70.0,
        })
        lid = resp.json()["id"]
        assert client.get(f"/api/listings/{lid}").json()["status"] == "draft"

        # Not on marketplace yet
        assert len(client.get("/api/marketplace").json()) == 0

        # Approve
        client.post("/api/listings/batch-approve", json={"ids": [lid]})
        assert client.get(f"/api/listings/{lid}").json()["status"] == "active"

        # Now on marketplace
        marketplace = client.get("/api/marketplace").json()
        assert len(marketplace) == 1
        assert "min_price" not in marketplace[0]

        # Offer at asking
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Alice",
            "buyer_phone": "202-555-1234", "offer_amount": 100.0,
        })
        assert resp.json()["decision"] == "accepted"

        # Verify offer stored
        offers = client.get(f"/api/listings/{lid}/offers").json()
        assert len(offers) == 1
        assert offers[0]["status"] == "accepted"

    def test_draft_approve_offer_reject_counter_accept(self, client):
        """Buyer lowballs, gets rejected, comes back at asking."""
        resp = client.post("/api/listings", json={
            "title": "Fancy Chair", "asking_price": 500.0, "min_price": 350.0,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        # Low offer
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Bob",
            "buyer_phone": "555-1111", "offer_amount": 200.0,
        })
        assert resp.json()["decision"] == "rejected"

        # Try again at min
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Bob",
            "buyer_phone": "555-1111", "offer_amount": 350.0,
        })
        assert resp.json()["decision"] == "accepted"

        # Two offers stored
        offers = client.get(f"/api/listings/{lid}/offers").json()
        assert len(offers) == 2

    def test_draft_edit_then_approve(self, client):
        """Edit all fields while in draft, then approve."""
        resp = client.post("/api/listings", json={"title": "Raw Draft"})
        lid = resp.json()["id"]

        # Edit each field
        client.put(f"/api/listings/{lid}", json={"title": "Polished Item"})
        client.put(f"/api/listings/{lid}", json={"description": "Thoroughly cleaned"})
        client.put(f"/api/listings/{lid}", json={"asking_price": 150.0})
        client.put(f"/api/listings/{lid}", json={"min_price": 100.0})
        client.put(f"/api/listings/{lid}", json={"category": "furniture"})
        client.put(f"/api/listings/{lid}", json={"condition": "excellent"})

        listing = client.get(f"/api/listings/{lid}").json()
        assert listing["title"] == "Polished Item"
        assert listing["description"] == "Thoroughly cleaned"
        assert listing["asking_price"] == 150.0
        assert listing["min_price"] == 100.0
        assert listing["category"] == "furniture"
        assert listing["condition"] == "excellent"
        assert listing["status"] == "draft"

        # Approve
        client.post("/api/listings/batch-approve", json={"ids": [lid]})
        assert client.get(f"/api/listings/{lid}").json()["status"] == "active"

    def test_create_approve_sell_relist(self, client):
        """Full cycle: draft -> active -> sold -> active again."""
        resp = client.post("/api/listings", json={
            "title": "Reusable Item", "asking_price": 75.0,
        })
        lid = resp.json()["id"]

        client.post("/api/listings/batch-approve", json={"ids": [lid]})
        assert len(client.get("/api/marketplace").json()) == 1

        client.put(f"/api/listings/{lid}", json={"status": "sold"})
        assert len(client.get("/api/marketplace").json()) == 0

        # Relist
        client.put(f"/api/listings/{lid}", json={"status": "active"})
        assert len(client.get("/api/marketplace").json()) == 1

    def test_delete_mid_lifecycle(self, client):
        """Delete an active listing with offers."""
        resp = client.post("/api/listings", json={
            "title": "Doomed", "asking_price": 100.0, "min_price": 70.0,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        # Add some offers
        for i in range(3):
            client.post("/api/offers", json={
                "listing_id": lid, "buyer_name": f"Buyer{i}",
                "buyer_phone": f"555-{i}", "offer_amount": 80.0,
            })

        # Delete
        resp = client.delete(f"/api/listings/{lid}")
        assert resp.status_code == 200

        # Gone from everywhere
        assert client.get(f"/api/listings/{lid}").status_code == 404
        assert len(client.get("/api/marketplace").json()) == 0


class TestPayloadValidation:
    def test_malformed_json(self, client):
        resp = client.post(
            "/api/listings",
            content=b"not json at all",
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 422

    def test_wrong_type_for_price(self, client):
        resp = client.post("/api/listings", json={
            "title": "Item", "asking_price": "not a number",
        })
        assert resp.status_code == 422

    def test_extra_fields_ignored(self, client):
        resp = client.post("/api/listings", json={
            "title": "Item", "asking_price": 50.0,
            "nonexistent_field": "should be ignored",
        })
        assert resp.status_code == 201

    def test_null_values_accepted(self, client):
        resp = client.post("/api/listings", json={
            "title": "Item", "description": None, "asking_price": None,
        })
        assert resp.status_code == 201

    def test_batch_approve_wrong_type(self, client):
        resp = client.post("/api/listings/batch-approve", json={"ids": "not a list"})
        assert resp.status_code == 422

    def test_batch_approve_string_ids(self, client):
        resp = client.post("/api/listings/batch-approve", json={"ids": ["a", "b"]})
        assert resp.status_code == 422

    def test_offer_missing_listing_id(self, client):
        resp = client.post("/api/offers", json={
            "buyer_name": "X", "buyer_phone": "555", "offer_amount": 50.0,
        })
        assert resp.status_code == 422

    def test_offer_string_amount(self, client):
        resp = client.post("/api/listings", json={"title": "T", "asking_price": 100})
        lid = resp.json()["id"]
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "X",
            "buyer_phone": "555", "offer_amount": "fifty bucks",
        })
        assert resp.status_code == 422


class TestMultipleListingsInteraction:
    def test_offers_isolated_between_listings(self, client):
        """Offers on listing A don't show up on listing B."""
        resp1 = client.post("/api/listings", json={"title": "A", "asking_price": 100, "min_price": 70})
        resp2 = client.post("/api/listings", json={"title": "B", "asking_price": 200, "min_price": 140})
        lid1, lid2 = resp1.json()["id"], resp2.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid1, lid2]})

        client.post("/api/offers", json={
            "listing_id": lid1, "buyer_name": "X", "buyer_phone": "1", "offer_amount": 80,
        })
        client.post("/api/offers", json={
            "listing_id": lid1, "buyer_name": "Y", "buyer_phone": "2", "offer_amount": 90,
        })
        client.post("/api/offers", json={
            "listing_id": lid2, "buyer_name": "Z", "buyer_phone": "3", "offer_amount": 150,
        })

        assert len(client.get(f"/api/listings/{lid1}/offers").json()) == 2
        assert len(client.get(f"/api/listings/{lid2}/offers").json()) == 1

    def test_delete_one_doesnt_affect_other(self, client):
        resp1 = client.post("/api/listings", json={"title": "Keep", "asking_price": 100})
        resp2 = client.post("/api/listings", json={"title": "Delete", "asking_price": 200})
        lid1, lid2 = resp1.json()["id"], resp2.json()["id"]

        client.delete(f"/api/listings/{lid2}")
        assert client.get(f"/api/listings/{lid1}").status_code == 200
        assert client.get(f"/api/listings/{lid2}").status_code == 404

    def test_marketplace_returns_all_active(self, client):
        """All active items appear on marketplace."""
        created = []
        for name in ["Alpha", "Beta", "Gamma"]:
            resp = client.post("/api/listings", json={"title": name, "asking_price": 100})
            created.append(resp.json()["id"])
        client.post("/api/listings/batch-approve", json={"ids": created})

        marketplace = client.get("/api/marketplace").json()
        titles = sorted(m["title"] for m in marketplace)
        assert titles == ["Alpha", "Beta", "Gamma"]


class TestNegotiationThroughAPI:
    """Test all negotiation paths via the actual API endpoint."""

    def _make_listing(self, client, asking=100.0, min_price=70.0):
        resp = client.post("/api/listings", json={
            "title": "Test", "asking_price": asking, "min_price": min_price,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})
        return lid

    def test_accept_at_asking(self, client):
        lid = self._make_listing(client, 100, 70)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "A", "buyer_phone": "1", "offer_amount": 100,
        })
        assert resp.json()["decision"] == "accepted"

    def test_accept_above_asking(self, client):
        lid = self._make_listing(client, 100, 70)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "A", "buyer_phone": "1", "offer_amount": 150,
        })
        assert resp.json()["decision"] == "accepted"

    def test_accept_at_min(self, client):
        lid = self._make_listing(client, 100, 70)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "A", "buyer_phone": "1", "offer_amount": 70,
        })
        assert resp.json()["decision"] == "accepted"

    def test_accept_between_min_and_asking(self, client):
        lid = self._make_listing(client, 100, 70)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "A", "buyer_phone": "1", "offer_amount": 85,
        })
        assert resp.json()["decision"] == "accepted"

    def test_reject_below_min(self, client):
        lid = self._make_listing(client, 100, 70)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "A", "buyer_phone": "1", "offer_amount": 50,
        })
        data = resp.json()
        assert data["decision"] == "rejected"
        assert "100" in data["message"]

    def test_reject_zero(self, client):
        lid = self._make_listing(client, 100, 70)
        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "A", "buyer_phone": "1", "offer_amount": 0,
        })
        assert resp.json()["decision"] == "rejected"

    def test_pending_no_min_price(self, client):
        resp = client.post("/api/listings", json={
            "title": "No Min", "asking_price": 100.0,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "A", "buyer_phone": "1", "offer_amount": 80,
        })
        assert resp.json()["decision"] == "pending"

    def test_accept_at_asking_even_without_min(self, client):
        resp = client.post("/api/listings", json={
            "title": "No Min", "asking_price": 100.0,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        resp = client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "A", "buyer_phone": "1", "offer_amount": 100,
        })
        assert resp.json()["decision"] == "accepted"

    def test_offer_response_persisted(self, client):
        """Verify negotiation result is stored in the offer record."""
        lid = self._make_listing(client, 100, 70)

        # Accepted offer
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Accept", "buyer_phone": "1", "offer_amount": 100,
        })
        # Rejected offer
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Reject", "buyer_phone": "2", "offer_amount": 30,
        })

        offers = client.get(f"/api/listings/{lid}/offers").json()
        statuses = {o["buyer_name"]: o["status"] for o in offers}
        assert statuses["Accept"] == "accepted"
        assert statuses["Reject"] == "rejected"

        # Verify response_message is populated
        for offer in offers:
            assert offer["response_message"] is not None
            assert len(offer["response_message"]) > 0
