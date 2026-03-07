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
    # Import after setting env var so app picks it up
    from backend.api import app, _get_db_path
    _get_db_path.cache_clear()
    with TestClient(app) as c:
        yield c
    os.unlink(db_path)


@pytest.fixture
def draft_listing(client):
    resp = client.post("/api/listings", json={
        "title": "Test Item", "description": "A test", "category": "electronics",
        "condition": "good", "asking_price": 100.0, "min_price": 70.0,
    })
    return resp.json()["id"]


class TestHealth:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestListings:
    def test_create_listing(self, client):
        resp = client.post("/api/listings", json={
            "title": "Desk", "asking_price": 150.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == 1
        assert data["status"] == "draft"

    def test_get_listing(self, client, draft_listing):
        resp = client.get(f"/api/listings/{draft_listing}")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Test Item"

    def test_get_listing_not_found(self, client):
        resp = client.get("/api/listings/999")
        assert resp.status_code == 404

    def test_list_listings(self, client, draft_listing):
        resp = client.get("/api/listings")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_listings_by_status(self, client, draft_listing):
        resp = client.get("/api/listings?status=draft")
        assert len(resp.json()) == 1
        resp = client.get("/api/listings?status=active")
        assert len(resp.json()) == 0

    def test_update_listing(self, client, draft_listing):
        resp = client.put(f"/api/listings/{draft_listing}", json={
            "title": "Updated Item", "asking_price": 120.0,
        })
        assert resp.status_code == 200
        assert resp.json()["message"] == "updated"

    def test_update_listing_not_found(self, client):
        resp = client.put("/api/listings/999", json={"title": "X"})
        assert resp.status_code == 404

    def test_delete_listing(self, client, draft_listing):
        resp = client.delete(f"/api/listings/{draft_listing}")
        assert resp.status_code == 200
        resp = client.get(f"/api/listings/{draft_listing}")
        assert resp.status_code == 404

    def test_delete_listing_not_found(self, client):
        resp = client.delete("/api/listings/999")
        assert resp.status_code == 404

    def test_batch_approve(self, client):
        id1 = client.post("/api/listings", json={"title": "A", "asking_price": 10}).json()["id"]
        id2 = client.post("/api/listings", json={"title": "B", "asking_price": 20}).json()["id"]
        resp = client.post("/api/listings/batch-approve", json={"ids": [id1, id2]})
        assert resp.status_code == 200
        assert resp.json()["updated"] == 2
        # Verify both are active
        r1 = client.get(f"/api/listings/{id1}").json()
        r2 = client.get(f"/api/listings/{id2}").json()
        assert r1["status"] == "active"
        assert r2["status"] == "active"


class TestMarketplace:
    def test_marketplace_only_active(self, client, draft_listing):
        # Draft not visible
        resp = client.get("/api/marketplace")
        assert resp.status_code == 200
        assert len(resp.json()) == 0
        # Approve it
        client.post("/api/listings/batch-approve", json={"ids": [draft_listing]})
        resp = client.get("/api/marketplace")
        assert len(resp.json()) == 1

    def test_marketplace_hides_min_price(self, client, draft_listing):
        client.post("/api/listings/batch-approve", json={"ids": [draft_listing]})
        resp = client.get("/api/marketplace")
        item = resp.json()[0]
        assert "min_price" not in item
        assert "asking_price" in item


class TestOffers:
    def test_create_offer(self, client, draft_listing):
        client.post("/api/listings/batch-approve", json={"ids": [draft_listing]})
        resp = client.post("/api/offers", json={
            "listing_id": draft_listing, "buyer_name": "Alice",
            "buyer_phone": "555-1234", "offer_amount": 100.0,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "offer_id" in data
        assert "decision" in data

    def test_list_offers(self, client, draft_listing):
        client.post("/api/listings/batch-approve", json={"ids": [draft_listing]})
        client.post("/api/offers", json={
            "listing_id": draft_listing, "buyer_name": "Bob",
            "buyer_phone": "555-5678", "offer_amount": 80.0,
        })
        resp = client.get(f"/api/listings/{draft_listing}/offers")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
