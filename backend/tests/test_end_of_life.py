"""Tests for end-of-life status transitions (donate/store)."""
import pytest
from datetime import date, timedelta
from backend.database import init_db
from backend.models import (
    ListingCreate, ListingUpdate,
    create_listing, update_listing, get_listing, list_listings,
)

@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path

@pytest.fixture
def client(db_path):
    import os
    os.environ["DB_PATH"] = db_path
    from backend.api import app, _get_db_path
    _get_db_path.cache_clear()
    from fastapi.testclient import TestClient
    return TestClient(app)


class TestStatusTransitions:
    def test_can_set_status_to_donate(self, db_path):
        lid = create_listing(ListingCreate(title="Old Chair"), db_path)
        update_listing(lid, ListingUpdate(status="donate"), db_path)
        listing = get_listing(lid, db_path)
        assert listing.status == "donate"

    def test_can_set_status_to_store(self, db_path):
        lid = create_listing(ListingCreate(title="Watch"), db_path)
        update_listing(lid, ListingUpdate(status="store"), db_path)
        listing = get_listing(lid, db_path)
        assert listing.status == "store"

    def test_donate_not_in_marketplace(self, client, db_path):
        lid = create_listing(ListingCreate(title="Chair", asking_price=50.0), db_path)
        deadline = (date.today() + timedelta(days=30)).isoformat()
        update_listing(lid, ListingUpdate(status="donate", deadline=deadline), db_path)
        res = client.get("/api/marketplace")
        assert len(res.json()) == 0

    def test_store_not_in_marketplace(self, client, db_path):
        lid = create_listing(ListingCreate(title="Watch", asking_price=500.0), db_path)
        deadline = (date.today() + timedelta(days=30)).isoformat()
        update_listing(lid, ListingUpdate(status="store", deadline=deadline), db_path)
        res = client.get("/api/marketplace")
        assert len(res.json()) == 0

    def test_list_by_donate_status(self, db_path):
        lid = create_listing(ListingCreate(title="Lamp"), db_path)
        update_listing(lid, ListingUpdate(status="donate"), db_path)
        results = list_listings(status="donate", db_path=db_path)
        assert len(results) == 1
        assert results[0].title == "Lamp"

    def test_list_by_store_status(self, db_path):
        lid = create_listing(ListingCreate(title="Ring"), db_path)
        update_listing(lid, ListingUpdate(status="store"), db_path)
        results = list_listings(status="store", db_path=db_path)
        assert len(results) == 1


class TestBatchStatusEndpoint:
    def test_batch_donate(self, client, db_path):
        lid1 = create_listing(ListingCreate(title="A"), db_path)
        lid2 = create_listing(ListingCreate(title="B"), db_path)
        update_listing(lid1, ListingUpdate(status="active"), db_path)
        update_listing(lid2, ListingUpdate(status="active"), db_path)
        res = client.post("/api/listings/batch-status", json={"ids": [lid1, lid2], "status": "donate"})
        assert res.status_code == 200
        assert res.json()["updated"] == 2

    def test_batch_store(self, client, db_path):
        lid = create_listing(ListingCreate(title="Watch"), db_path)
        update_listing(lid, ListingUpdate(status="active"), db_path)
        res = client.post("/api/listings/batch-status", json={"ids": [lid], "status": "store"})
        assert res.status_code == 200
        assert res.json()["updated"] == 1
