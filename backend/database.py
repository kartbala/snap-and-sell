import os
import sqlite3

DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "snap_and_sell.db"
)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    condition TEXT,
    asking_price REAL,
    min_price REAL,
    original_price REAL,
    purchase_date TEXT,
    purchase_source TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    location TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    buyer_name TEXT NOT NULL,
    buyer_phone TEXT NOT NULL,
    buyer_email TEXT,
    offer_amount REAL NOT NULL,
    message TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    response_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
);
"""


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.close()


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
