"""Tests for price comparisons storage and retrieval."""

import os
import json
import tempfile
import pytest
from fastapi.testclient import TestClient
from backend.database import init_db
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


SAMPLE_COMPS = json.dumps([
    {"source": "eBay", "price": 450.0, "url": "https://ebay.com/item/123", "note": "sold listing"},
    {"source": "FB Marketplace", "price": 500.0, "url": None, "note": "asking price"},
    {"source": "Swappa", "price": 425.0, "url": "https://swappa.com/item/456", "note": "good condition"},
])


class TestPriceCompsModel:
    def test_create_listing_with_comps(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="TV", asking_price=500, price_comps=SAMPLE_COMPS),
            db_path,
        )
        listing = models.get_listing(lid, db_path)
        assert listing.price_comps is not None
        comps = json.loads(listing.price_comps)
        assert len(comps) == 3
        assert comps[0]["source"] == "eBay"

    def test_create_listing_without_comps(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Chair", asking_price=200),
            db_path,
        )
        listing = models.get_listing(lid, db_path)
        assert listing.price_comps is None

    def test_update_listing_add_comps(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="TV", asking_price=500), db_path
        )
        models.update_listing(lid, models.ListingUpdate(price_comps=SAMPLE_COMPS), db_path)
        listing = models.get_listing(lid, db_path)
        assert listing.price_comps is not None
        comps = json.loads(listing.price_comps)
        assert len(comps) == 3

    def test_marketplace_includes_comps(self, client):
        resp = client.post("/api/listings", json={
            "title": "TV", "asking_price": 500, "price_comps": SAMPLE_COMPS,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        marketplace = client.get("/api/marketplace").json()
        assert len(marketplace) == 1
        assert marketplace[0]["price_comps"] is not None
        comps = json.loads(marketplace[0]["price_comps"])
        assert len(comps) == 3


class TestShareUrlModel:
    def test_create_listing_share_url_null(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Item", asking_price=100), db_path
        )
        listing = models.get_listing(lid, db_path)
        assert listing.share_url is None

    def test_update_listing_set_share_url(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Item", asking_price=100), db_path
        )
        models.update_listing(
            lid, models.ListingUpdate(share_url="https://karthik.link/item-1"), db_path
        )
        listing = models.get_listing(lid, db_path)
        assert listing.share_url == "https://karthik.link/item-1"

    def test_marketplace_includes_share_url(self, client):
        resp = client.post("/api/listings", json={
            "title": "Item", "asking_price": 100,
        })
        lid = resp.json()["id"]
        client.put(f"/api/listings/{lid}", json={"share_url": "https://karthik.link/test"})
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        marketplace = client.get("/api/marketplace").json()
        assert marketplace[0]["share_url"] == "https://karthik.link/test"
