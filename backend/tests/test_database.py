import os
import sqlite3
import tempfile
import pytest
from backend.database import init_db, get_connection


@pytest.fixture
def db_path():
    """Create a temporary database for each test."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


class TestInitDb:
    def test_creates_listings_table(self, db_path):
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='listings'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_photos_table(self, db_path):
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='photos'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_creates_offers_table(self, db_path):
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='offers'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_listings_columns(self, db_path):
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("PRAGMA table_info(listings)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            "id", "title", "description", "category", "condition",
            "asking_price", "min_price", "original_price", "purchase_date",
            "purchase_source", "status", "location", "created_at", "updated_at",
        }
        assert expected == columns
        conn.close()

    def test_photos_columns(self, db_path):
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("PRAGMA table_info(photos)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {"id", "listing_id", "file_path", "is_primary"}
        assert expected == columns
        conn.close()

    def test_offers_columns(self, db_path):
        init_db(db_path)
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("PRAGMA table_info(offers)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            "id", "listing_id", "buyer_name", "buyer_phone", "buyer_email",
            "offer_amount", "message", "status", "response_message", "created_at",
        }
        assert expected == columns
        conn.close()

    def test_idempotent(self, db_path):
        init_db(db_path)
        init_db(db_path)  # Should not raise
        conn = sqlite3.connect(db_path)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert tables == {"listings", "photos", "offers"}
        conn.close()


class TestGetConnection:
    def test_returns_connection(self, db_path):
        init_db(db_path)
        conn = get_connection(db_path)
        assert isinstance(conn, sqlite3.Connection)
        conn.close()

    def test_row_factory(self, db_path):
        init_db(db_path)
        conn = get_connection(db_path)
        assert conn.row_factory == sqlite3.Row
        conn.close()

    def test_foreign_keys_enabled(self, db_path):
        init_db(db_path)
        conn = get_connection(db_path)
        cursor = conn.execute("PRAGMA foreign_keys")
        assert cursor.fetchone()[0] == 1
        conn.close()
