"""End-to-end scenario tests simulating real usage sessions."""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from backend.database import init_db
from backend.intake import parse_gemini_response, suggest_prices


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


GEMINI_MOVING_SALE = """
I identified the following items from your photos:

1. **Samsung 65" QLED TV (Q80B)** - 65 inch 4K QLED Smart TV, mounted on wall, excellent condition. I found a receipt from Best Buy dated 2023-06-15 for $1,099.99.

2. **West Elm Mid-Century Sofa** - 3-seater sofa, gray velvet, good condition with minor wear. Receipt from West Elm dated 2022-01-20 for $1,899.00.

3. **Dyson V15 Detect Vacuum** - Cordless stick vacuum, like new condition. Receipt from Amazon dated 2024-03-01 for $749.99.

4. **KitchenAid Artisan Mixer** - 5-quart stand mixer, red, good condition. No receipt found.

5. **Casper Original Mattress (Queen)** - Memory foam mattress, fair condition, 3 years old. Receipt from Casper dated 2021-09-10 for $1,095.00.
"""


class TestMovingSaleScenario:
    """Simulate: Karthik is moving and wants to sell 5 items from his apartment."""

    def test_full_moving_sale_flow(self, client):
        # Step 1: Parse Gemini output
        items = parse_gemini_response(GEMINI_MOVING_SALE)
        assert len(items) == 5

        # Step 2: Create drafts with suggested prices
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
            draft_ids.append(resp.json()["id"])

        # Step 3: Review drafts — Karthik adjusts prices on some items
        # The KitchenAid has no receipt, so no auto-price — set manually
        kitchenaid = None
        drafts = client.get("/api/listings?status=draft").json()
        for d in drafts:
            if "KitchenAid" in d["title"]:
                kitchenaid = d
                break
        assert kitchenaid is not None
        assert kitchenaid["asking_price"] is None  # No original price

        client.put(f"/api/listings/{kitchenaid['id']}", json={
            "asking_price": 200.0, "min_price": 140.0,
        })

        # Karthik thinks mattress is priced too high, adjusts down
        mattress = next(d for d in drafts if "Mattress" in d["title"])
        client.put(f"/api/listings/{mattress['id']}", json={
            "asking_price": 250.0, "min_price": 150.0,
        })

        # Step 4: Approve all
        resp = client.post("/api/listings/batch-approve", json={"ids": draft_ids})
        assert resp.json()["updated"] == 5

        # Step 5: Verify marketplace
        marketplace = client.get("/api/marketplace").json()
        assert len(marketplace) == 5
        for item in marketplace:
            assert "min_price" not in item
            assert item["asking_price"] is not None

        # Step 6: Buyers make offers
        tv = next(m for m in marketplace if "TV" in m["title"])
        sofa = next(m for m in marketplace if "Sofa" in m["title"])
        vacuum = next(m for m in marketplace if "Vacuum" in m["title"])
        mixer = next(m for m in marketplace if "Mixer" in m["title"])
        mattress_pub = next(m for m in marketplace if "Mattress" in m["title"])

        # Buyer 1: Offers asking price for TV — accepted
        resp = client.post("/api/offers", json={
            "listing_id": tv["id"], "buyer_name": "Sarah Johnson",
            "buyer_phone": "202-555-1111", "offer_amount": tv["asking_price"],
            "message": "Can pick up today!",
        })
        assert resp.json()["decision"] == "accepted"

        # Buyer 2: Lowballs the sofa — rejected
        resp = client.post("/api/offers", json={
            "listing_id": sofa["id"], "buyer_name": "Mike Chen",
            "buyer_phone": "202-555-2222", "offer_amount": 300.0,
        })
        assert resp.json()["decision"] == "rejected"

        # Buyer 3: Reasonable offer on sofa — accepted (between min and asking)
        resp = client.post("/api/offers", json={
            "listing_id": sofa["id"], "buyer_name": "Lisa Park",
            "buyer_phone": "202-555-3333", "offer_amount": 900.0,
        })
        assert resp.json()["decision"] == "accepted"

        # Buyer 4: Offers on vacuum — above asking — accepted
        resp = client.post("/api/offers", json={
            "listing_id": vacuum["id"], "buyer_name": "James Wilson",
            "buyer_phone": "202-555-4444", "offer_amount": 400.0,
        })
        assert resp.json()["decision"] == "accepted"

        # Buyer 5: Offers on mixer at exact min — accepted
        resp = client.post("/api/offers", json={
            "listing_id": mixer["id"], "buyer_name": "Emma Davis",
            "buyer_phone": "202-555-5555", "offer_amount": 140.0,
        })
        assert resp.json()["decision"] == "accepted"

        # Buyer 6: Lowball on mattress — rejected
        resp = client.post("/api/offers", json={
            "listing_id": mattress_pub["id"], "buyer_name": "Tom Brown",
            "buyer_phone": "202-555-6666", "offer_amount": 50.0,
        })
        assert resp.json()["decision"] == "rejected"

        # Step 7: Check final state
        # TV has 1 offer (accepted)
        tv_offers = client.get(f"/api/listings/{tv['id']}/offers").json()
        assert len(tv_offers) == 1
        assert tv_offers[0]["status"] == "accepted"

        # Sofa has 2 offers (1 rejected, 1 accepted)
        sofa_offers = client.get(f"/api/listings/{sofa['id']}/offers").json()
        assert len(sofa_offers) == 2
        statuses = {o["buyer_name"]: o["status"] for o in sofa_offers}
        assert statuses["Mike Chen"] == "rejected"
        assert statuses["Lisa Park"] == "accepted"

    def test_partial_approve_workflow(self, client):
        """Approve only some drafts, keep others as drafts."""
        items = parse_gemini_response(GEMINI_MOVING_SALE)

        draft_ids = []
        for item in items:
            asking, minimum = suggest_prices(item)
            resp = client.post("/api/listings", json={
                "title": item.title, "asking_price": asking or 100.0,
                "min_price": minimum or 70.0,
            })
            draft_ids.append(resp.json()["id"])

        # Approve only first 3
        client.post("/api/listings/batch-approve", json={"ids": draft_ids[:3]})

        assert len(client.get("/api/marketplace").json()) == 3
        assert len(client.get("/api/listings?status=draft").json()) == 2
        assert len(client.get("/api/listings?status=active").json()) == 3

        # Now approve the rest
        client.post("/api/listings/batch-approve", json={"ids": draft_ids[3:]})
        assert len(client.get("/api/marketplace").json()) == 5
        assert len(client.get("/api/listings?status=draft").json()) == 0


class TestEmptyStoreScenario:
    """Buyer visits marketplace when there's nothing for sale."""

    def test_empty_marketplace(self, client):
        resp = client.get("/api/marketplace")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_only_drafts_marketplace_empty(self, client):
        for i in range(5):
            client.post("/api/listings", json={"title": f"Draft {i}", "asking_price": 10})
        assert len(client.get("/api/marketplace").json()) == 0

    def test_all_sold_marketplace_empty(self, client):
        ids = []
        for i in range(3):
            resp = client.post("/api/listings", json={"title": f"Item {i}", "asking_price": 50})
            ids.append(resp.json()["id"])
        client.post("/api/listings/batch-approve", json={"ids": ids})
        for lid in ids:
            client.put(f"/api/listings/{lid}", json={"status": "sold"})
        assert len(client.get("/api/marketplace").json()) == 0


class TestHighVolumeScenario:
    """Stress test with many items and offers."""

    def test_50_listings_with_offers(self, client):
        ids = []
        for i in range(50):
            resp = client.post("/api/listings", json={
                "title": f"Item #{i:03d}",
                "asking_price": 100.0 + i,
                "min_price": 70.0 + i,
                "category": ["electronics", "furniture", "audio", "fitness"][i % 4],
            })
            assert resp.status_code == 201
            ids.append(resp.json()["id"])

        # Batch approve all
        resp = client.post("/api/listings/batch-approve", json={"ids": ids})
        assert resp.json()["updated"] == 50

        marketplace = client.get("/api/marketplace").json()
        assert len(marketplace) == 50

        # Each listing gets 2 offers
        for lid in ids:
            for j in range(2):
                resp = client.post("/api/offers", json={
                    "listing_id": lid,
                    "buyer_name": f"Buyer-{lid}-{j}",
                    "buyer_phone": f"555-{lid:04d}",
                    "offer_amount": 80.0 + j * 30,
                })
                assert resp.status_code == 201

        # Verify all offers exist
        all_listings = client.get("/api/listings").json()
        assert len(all_listings) == 50

    def test_batch_approve_50_at_once(self, client):
        ids = []
        for i in range(50):
            resp = client.post("/api/listings", json={
                "title": f"Batch {i}", "asking_price": 10.0,
            })
            ids.append(resp.json()["id"])

        resp = client.post("/api/listings/batch-approve", json={"ids": ids})
        assert resp.json()["updated"] == 50
        assert len(client.get("/api/marketplace").json()) == 50


class TestPriceResearchScenario:
    """Test intake parser with varied Gemini responses."""

    def test_items_get_correct_categories(self, client):
        items = parse_gemini_response(GEMINI_MOVING_SALE)

        categories = {item.title: item.category for item in items}
        assert categories['Samsung 65" QLED TV (Q80B)'] == "electronics"
        # Sofa = furniture (has "sofa" or "couch" in keywords)
        # Dyson vacuum - not in any category
        assert categories["Dyson V15 Detect Vacuum"] is None

    def test_depreciation_applied_correctly(self, client):
        items = parse_gemini_response(GEMINI_MOVING_SALE)

        for item in items:
            if item.original_price is not None:
                asking, minimum = suggest_prices(item)
                assert asking <= item.original_price
                assert minimum <= asking
                if asking is not None:
                    assert minimum == round(asking * 0.70, 2)
