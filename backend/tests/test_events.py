"""Tests for click/view event tracking."""
import os
import pytest
from backend.database import init_db
from backend.events import record_event, list_events, event_summary


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


@pytest.fixture
def client(db_path):
    os.environ["DB_PATH"] = db_path
    from backend.api import app, _get_db_path
    _get_db_path.cache_clear()
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_record_and_list(db_path):
    eid = record_event("view", listing_id=1, session_id="s1", db_path=db_path)
    assert eid > 0
    events = list_events(listing_id=1, db_path=db_path)
    assert len(events) == 1
    assert events[0]["event_type"] == "view"
    assert events[0]["session_id"] == "s1"


def test_record_event_listing_optional(db_path):
    # Page-level events (marketplace view) carry no listing_id.
    eid = record_event("marketplace_view", session_id="s1", db_path=db_path)
    assert eid > 0
    assert list_events(event_type="marketplace_view", db_path=db_path)[0]["listing_id"] is None


def test_summary_counts_and_unique_sessions(db_path):
    record_event("view", listing_id=1, session_id="a", db_path=db_path)
    record_event("view", listing_id=1, session_id="a", db_path=db_path)  # same session
    record_event("view", listing_id=1, session_id="b", db_path=db_path)
    record_event("payment_click", listing_id=1, target="venmo", session_id="b", db_path=db_path)

    summary = event_summary(db_path)
    view = next(r for r in summary if r["event_type"] == "view")
    assert view["count"] == 3
    assert view["unique_sessions"] == 2
    pay = next(r for r in summary if r["event_type"] == "payment_click")
    assert pay["count"] == 1


def test_post_event_endpoint_captures_headers(client):
    resp = client.post(
        "/api/events",
        json={"event_type": "payment_click", "listing_id": 7, "target": "venmo",
              "session_id": "s9"},
        headers={"User-Agent": "pytest-UA", "Referer": "https://example.com/m/7"},
    )
    assert resp.status_code == 201
    assert resp.json()["id"] > 0

    summary = client.get("/api/events/summary").json()
    assert summary["totals"]["payment_click"] == 1
    assert any(r["listing_id"] == 7 for r in summary["by_listing"])


def test_summary_empty(client):
    summary = client.get("/api/events/summary").json()
    assert summary["totals"] == {}
    assert summary["by_listing"] == []
