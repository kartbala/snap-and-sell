"""Tests for share link generation."""

import os
import json
import tempfile
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from backend.database import init_db
from backend import models
from backend.share import generate_slashtag, create_short_link


class TestSlashtagGeneration:
    def test_simple_title(self):
        assert generate_slashtag("Samsung TV") == "samsung-tv"

    def test_special_characters(self):
        assert generate_slashtag('KitchenAid 5-Qt Mixer (Red)') == "kitchenaid-5-qt-mixer-red"

    def test_long_title_truncated(self):
        tag = generate_slashtag("Super Incredibly Long Product Name That Goes On Forever")
        assert len(tag) <= 50

    def test_quotes_and_inches(self):
        assert generate_slashtag('Samsung 65" QLED TV') == "samsung-65-qled-tv"

    def test_empty_title(self):
        tag = generate_slashtag("")
        assert len(tag) > 0  # should generate a fallback


class TestCreateShortLink:
    @patch("backend.share._call_rebrandly")
    def test_returns_short_url(self, mock_call):
        mock_call.return_value = {
            "shortUrl": "https://karthik.link/samsung-tv",
            "slashtag": "samsung-tv",
        }
        url = create_short_link("Samsung TV", 1, "http://localhost:5173")
        assert url == "https://karthik.link/samsung-tv"

    @patch("backend.share._call_rebrandly")
    def test_passes_correct_payload(self, mock_call):
        mock_call.return_value = {"shortUrl": "https://karthik.link/test"}
        create_short_link("Test Item", 42, "http://localhost:5173")
        call_args = mock_call.call_args[0][0]
        assert call_args["destination"] == "http://localhost:5173/?item=42"
        assert call_args["slashtag"] == "test-item"
        assert call_args["domain"]["fullName"] == "karthik.link"

    @patch("backend.share._call_rebrandly")
    def test_api_error_returns_none(self, mock_call):
        mock_call.side_effect = Exception("API error")
        url = create_short_link("Fail", 1, "http://localhost:5173")
        assert url is None


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


class TestShareEndpoint:
    @patch("backend.share.create_short_link")
    def test_share_active_listing(self, mock_create, client):
        mock_create.return_value = "https://karthik.link/widget"
        resp = client.post("/api/listings", json={
            "title": "Widget", "asking_price": 100,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        resp = client.post(f"/api/listings/{lid}/share")
        assert resp.status_code == 200
        assert resp.json()["share_url"] == "https://karthik.link/widget"

        # Verify stored on listing
        listing = client.get(f"/api/listings/{lid}").json()
        assert listing["share_url"] == "https://karthik.link/widget"

    @patch("backend.share.create_short_link")
    def test_share_returns_existing_url(self, mock_create, client):
        """If share_url already exists, return it without calling Rebrandly."""
        resp = client.post("/api/listings", json={
            "title": "Widget", "asking_price": 100,
        })
        lid = resp.json()["id"]
        client.put(f"/api/listings/{lid}", json={"share_url": "https://karthik.link/existing"})
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        resp = client.post(f"/api/listings/{lid}/share")
        assert resp.json()["share_url"] == "https://karthik.link/existing"
        mock_create.assert_not_called()

    def test_share_nonexistent_listing(self, client):
        resp = client.post("/api/listings/999/share")
        assert resp.status_code == 404

    @patch("backend.share.create_short_link")
    def test_share_api_failure(self, mock_create, client):
        mock_create.return_value = None
        resp = client.post("/api/listings", json={
            "title": "Widget", "asking_price": 100,
        })
        lid = resp.json()["id"]
        client.post("/api/listings/batch-approve", json={"ids": [lid]})

        resp = client.post(f"/api/listings/{lid}/share")
        assert resp.status_code == 502
        assert "Rebrandly" in resp.json()["detail"]
