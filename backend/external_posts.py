"""CRUD for external cross-posting records."""
from __future__ import annotations
from backend.database import get_connection, DEFAULT_DB_PATH


def create_external_post(
    listing_id: int,
    platform: str,
    url: str | None = None,
    last_price_posted: float | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    conn = get_connection(db_path)
    cursor = conn.execute(
        "INSERT INTO external_posts (listing_id, platform, url, last_price_posted) VALUES (?, ?, ?, ?)",
        (listing_id, platform, url, last_price_posted),
    )
    conn.commit()
    pid = cursor.lastrowid
    conn.close()
    return pid


def list_external_posts(
    listing_id: int | None = None,
    platform: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> list[dict]:
    conn = get_connection(db_path)
    query = "SELECT * FROM external_posts WHERE 1=1"
    params = []
    if listing_id is not None:
        query += " AND listing_id = ?"
        params.append(listing_id)
    if platform is not None:
        query += " AND platform = ?"
        params.append(platform)
    query += " ORDER BY posted_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_external_post_status(
    post_id: int, status: str, db_path: str = DEFAULT_DB_PATH,
) -> bool:
    conn = get_connection(db_path)
    cursor = conn.execute(
        "UPDATE external_posts SET status = ? WHERE id = ?",
        (status, post_id),
    )
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed


def get_stale_posts(db_path: str = DEFAULT_DB_PATH) -> list[dict]:
    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT * FROM external_posts WHERE status = 'price_stale' ORDER BY posted_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
