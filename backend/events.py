"""Click/view event tracking for funnel analytics.

Events are recorded by a tiny client-side beacon (see frontend) and snapshotted
nightly by the splunk-civic capture job, which polls /api/events/summary. The
summary is cumulative, so a git diff of two daily snapshots yields that day's
clicks. Known event types (free-form, not enforced):

    marketplace_view  marketplace page loaded
    view              listing detail viewed
    photo_open        lightbox opened on a listing
    contact_reveal    buyer opened the make-an-offer / contact flow
    share_click       a share link was clicked
    payment_click     outbound payment link clicked (target = venmo|zelle|cash)
    external_click    outbound cross-post link clicked (target = platform)
"""
from __future__ import annotations
from backend.database import get_connection, DEFAULT_DB_PATH


def record_event(
    event_type: str,
    listing_id: int | None = None,
    target: str | None = None,
    referrer: str | None = None,
    session_id: str | None = None,
    user_agent: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    conn = get_connection(db_path)
    cursor = conn.execute(
        """INSERT INTO events
               (listing_id, event_type, target, referrer, session_id, user_agent)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (listing_id, event_type, target, referrer, session_id, user_agent),
    )
    conn.commit()
    eid = cursor.lastrowid
    conn.close()
    return eid


def list_events(
    listing_id: int | None = None,
    event_type: str | None = None,
    since: str | None = None,
    db_path: str = DEFAULT_DB_PATH,
) -> list[dict]:
    conn = get_connection(db_path)
    query = "SELECT * FROM events WHERE 1=1"
    params: list = []
    if listing_id is not None:
        query += " AND listing_id = ?"
        params.append(listing_id)
    if event_type is not None:
        query += " AND event_type = ?"
        params.append(event_type)
    if since is not None:
        query += " AND created_at >= ?"
        params.append(since)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def event_summary(db_path: str = DEFAULT_DB_PATH) -> list[dict]:
    """Cumulative counts grouped by listing and event type.

    One row per (listing_id, event_type) with the running count and the most
    recent timestamp. This is what the nightly snapshot captures -- compact,
    PII-free, and diffable across days.
    """
    conn = get_connection(db_path)
    rows = conn.execute(
        """SELECT listing_id, event_type,
                  COUNT(*) AS count,
                  COUNT(DISTINCT session_id) AS unique_sessions,
                  MAX(created_at) AS last_event
           FROM events
           GROUP BY listing_id, event_type
           ORDER BY listing_id, event_type"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
