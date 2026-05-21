import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from backend.database import init_db


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
    with TestClient(app) as c:
        yield c


def _make_active(client, **overrides):
    payload = {
        "title": "Thing",
        "asking_price": 100.0,
        "min_price": 70.0,
        "original_price": 200.0,
        "deadline": "2099-01-01",
    }
    payload.update(overrides)
    resp = client.post("/api/listings", json=payload)
    lid = resp.json()["id"]
    client.post("/api/listings/batch-approve", json={"ids": [lid]})
    return lid


class TestFriendsMarketplace:
    def test_excludes_flagged_items(self, client):
        keep = _make_active(client, title="Keep me")
        skip = _make_active(client, title="Skip me", friends_excluded=True)
        resp = client.get("/api/friends-marketplace")
        assert resp.status_code == 200
        titles = [it["title"] for it in resp.json()]
        assert "Keep me" in titles
        assert "Skip me" not in titles
        ids = [it["id"] for it in resp.json()]
        assert keep in ids
        assert skip not in ids

    def test_strips_prices(self, client):
        _make_active(client)
        items = client.get("/api/friends-marketplace").json()
        assert len(items) == 1
        item = items[0]
        for field in (
            "asking_price",
            "min_price",
            "original_price",
            "price_comps",
            "share_url",
            "pricing_strategy",
        ):
            assert field not in item, f"{field} leaked to friends response"

    def test_keeps_descriptive_fields(self, client):
        _make_active(
            client,
            title="Bidet",
            description="Available June 1.",
            condition="good",
            category="home-goods",
            location="800 4th St SW",
        )
        item = client.get("/api/friends-marketplace").json()[0]
        assert item["title"] == "Bidet"
        assert item["description"] == "Available June 1."
        assert item["condition"] == "good"
        assert item["category"] == "home-goods"
        assert item["location"] == "800 4th St SW"
        assert "photos" in item

    def test_excludes_past_deadline_active(self, client):
        _make_active(client, title="Expired", deadline="2000-01-01")
        items = client.get("/api/friends-marketplace").json()
        assert items == []

    def test_includes_sold_items(self, client):
        lid = _make_active(client, title="Gone")
        client.post(
            "/api/listings/batch-status", json={"ids": [lid], "status": "sold"}
        )
        items = client.get("/api/friends-marketplace").json()
        assert len(items) == 1
        assert items[0]["status"] == "sold"

    def test_flag_via_update_endpoint(self, client):
        lid = _make_active(client, title="Toggle me")
        client.put(f"/api/listings/{lid}", json={"friends_excluded": True})
        items = client.get("/api/friends-marketplace").json()
        assert items == []
