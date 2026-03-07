"""End-to-end integration test: Gemini parse -> draft -> approve -> marketplace -> offers."""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from backend.database import init_db
from backend.intake import parse_gemini_response, suggest_prices


GEMINI_TEXT = """
I identified the following items from your photos:

1. **Sony WH-1000XM5 Headphones** - Over-ear noise canceling headphones, black, excellent condition. Receipt from Amazon dated 2024-06-15 for $349.99.

2. **IKEA BEKANT Standing Desk** - Electric sit/stand desk, white, 63x31 inches, good condition. Receipt from IKEA dated 2023-03-10 for $549.00.

3. **Bowflex SelectTech 552 Dumbbells** - Adjustable dumbbells, pair, like new condition. No receipt found.
"""


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


class TestFullFlow:
    def test_gemini_to_drafts_to_marketplace_to_offers(self, client):
        # Step 1: Parse Gemini text
        items = parse_gemini_response(GEMINI_TEXT)
        assert len(items) == 3

        # Step 2: Create draft listings from parsed items
        draft_ids = []
        for item in items:
            asking, minimum = suggest_prices(item)
            payload = {
                "title": item.title,
                "description": item.description,
                "category": item.category,
                "condition": item.condition,
                "asking_price": asking,
                "min_price": minimum,
                "original_price": item.original_price,
                "purchase_date": item.purchase_date,
                "purchase_source": item.purchase_source,
            }
            resp = client.post("/api/listings", json=payload)
            assert resp.status_code == 201
            assert resp.json()["status"] == "draft"
            draft_ids.append(resp.json()["id"])

        assert len(draft_ids) == 3

        # Step 3: Verify drafts exist
        resp = client.get("/api/listings?status=draft")
        assert resp.status_code == 200
        drafts = resp.json()
        assert len(drafts) == 3

        # Step 4: Batch approve all drafts
        resp = client.post("/api/listings/batch-approve", json={"ids": draft_ids})
        assert resp.status_code == 200
        assert resp.json()["updated"] == 3

        # Step 5: Verify active on marketplace
        resp = client.get("/api/marketplace")
        assert resp.status_code == 200
        marketplace = resp.json()
        assert len(marketplace) == 3
        # Verify min_price not exposed
        for item in marketplace:
            assert "min_price" not in item

        # Step 6: Submit offer at asking price -> auto-accept
        headphones = next(m for m in marketplace if "Headphones" in m["title"])
        resp = client.post("/api/offers", json={
            "listing_id": headphones["id"],
            "buyer_name": "Alice",
            "buyer_phone": "202-555-1234",
            "offer_amount": headphones["asking_price"],
        })
        assert resp.status_code == 201
        result = resp.json()
        assert result["decision"] == "accepted"

        # Step 7: Submit low offer -> auto-reject
        desk = next(m for m in marketplace if "Desk" in m["title"])
        resp = client.post("/api/offers", json={
            "listing_id": desk["id"],
            "buyer_name": "Bob",
            "buyer_phone": "202-555-5678",
            "offer_amount": 50.0,  # Way below min
        })
        assert resp.status_code == 201
        result = resp.json()
        assert result["decision"] == "rejected"

        # Step 8: Check offers list
        resp = client.get(f"/api/listings/{headphones['id']}/offers")
        assert resp.status_code == 200
        offers = resp.json()
        assert len(offers) == 1
        assert offers[0]["status"] == "accepted"

        resp = client.get(f"/api/listings/{desk['id']}/offers")
        assert resp.status_code == 200
        offers = resp.json()
        assert len(offers) == 1
        assert offers[0]["status"] == "rejected"

    def test_offer_on_item_without_min_price_is_pending(self, client):
        """Bowflex has no receipt -> no min price -> offer below asking is pending."""
        items = parse_gemini_response(GEMINI_TEXT)
        dumbbells = items[2]
        assert dumbbells.original_price is None

        resp = client.post("/api/listings", json={
            "title": dumbbells.title,
            "description": dumbbells.description,
            "category": dumbbells.category,
            "condition": dumbbells.condition,
            "asking_price": 150.0,  # Manual price since no original
            "min_price": None,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        resp = client.post("/api/offers", json={
            "listing_id": lid,
            "buyer_name": "Charlie",
            "buyer_phone": "202-555-9999",
            "offer_amount": 100.0,
        })
        assert resp.json()["decision"] == "pending"

    def test_offer_above_asking_accepted(self, client):
        resp = client.post("/api/listings", json={
            "title": "Test Item",
            "asking_price": 100.0,
            "min_price": 70.0,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        resp = client.post("/api/offers", json={
            "listing_id": lid,
            "buyer_name": "Eager Buyer",
            "buyer_phone": "202-555-0000",
            "offer_amount": 120.0,
        })
        assert resp.json()["decision"] == "accepted"
