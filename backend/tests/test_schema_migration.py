"""Tests for round 2 schema additions."""

import os
import tempfile
import pytest
from backend.database import init_db, get_connection


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


class TestNotificationsTable:
    def test_notifications_table_exists(self, db_path):
        conn = get_connection(db_path)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'"
        ).fetchone()
        conn.close()
        assert tables is not None

    def test_notifications_columns(self, db_path):
        conn = get_connection(db_path)
        cols = conn.execute("PRAGMA table_info(notifications)").fetchall()
        conn.close()
        names = {c["name"] for c in cols}
        assert names == {"id", "listing_id", "offer_id", "type", "sent", "created_at"}

    def test_notifications_fk_listing(self, db_path):
        conn = get_connection(db_path)
        fks = conn.execute("PRAGMA foreign_key_list(notifications)").fetchall()
        conn.close()
        tables = {fk["table"] for fk in fks}
        assert "listings" in tables
        assert "offers" in tables


class TestNewListingColumns:
    def test_price_comps_column_exists(self, db_path):
        conn = get_connection(db_path)
        cols = conn.execute("PRAGMA table_info(listings)").fetchall()
        conn.close()
        names = {c["name"] for c in cols}
        assert "price_comps" in names

    def test_share_url_column_exists(self, db_path):
        conn = get_connection(db_path)
        cols = conn.execute("PRAGMA table_info(listings)").fetchall()
        conn.close()
        names = {c["name"] for c in cols}
        assert "share_url" in names

    def test_price_comps_default_null(self, db_path):
        conn = get_connection(db_path)
        conn.execute("INSERT INTO listings (title) VALUES ('Test')")
        conn.commit()
        row = conn.execute("SELECT price_comps FROM listings WHERE title='Test'").fetchone()
        conn.close()
        assert row["price_comps"] is None

    def test_share_url_default_null(self, db_path):
        conn = get_connection(db_path)
        conn.execute("INSERT INTO listings (title) VALUES ('Test2')")
        conn.commit()
        row = conn.execute("SELECT share_url FROM listings WHERE title='Test2'").fetchone()
        conn.close()
        assert row["share_url"] is None


class TestLiquidationColumns:
    def test_listings_has_deadline_column(self, db_path):
        conn = get_connection(db_path)
        row = conn.execute("PRAGMA table_info(listings)").fetchall()
        columns = [r["name"] for r in row]
        conn.close()
        assert "deadline" in columns

    def test_listings_has_pricing_strategy_column(self, db_path):
        conn = get_connection(db_path)
        row = conn.execute("PRAGMA table_info(listings)").fetchall()
        columns = [r["name"] for r in row]
        conn.close()
        assert "pricing_strategy" in columns

    def test_listings_has_pickup_type_column(self, db_path):
        conn = get_connection(db_path)
        row = conn.execute("PRAGMA table_info(listings)").fetchall()
        columns = [r["name"] for r in row]
        conn.close()
        assert "pickup_type" in columns

    def test_external_posts_table_exists(self, db_path):
        conn = get_connection(db_path)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='external_posts'"
        ).fetchone()
        conn.close()
        assert row is not None
