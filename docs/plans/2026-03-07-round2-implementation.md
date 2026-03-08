# Round 2 Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add email notifications, price comparisons, and Rebrandly share links to the Snap & Sell marketplace.

**Architecture:** Notifications use a new DB table + API endpoints; price comps add a JSON column to listings stored during intake; share links call the Rebrandly REST API directly from a new endpoint. Schema migration via `init_db` additions. All features use TDD, extending existing 231-test suite.

**Tech Stack:** Python 3.11 + FastAPI, SQLite, React 19, Rebrandly REST API, `urllib.request` (no new deps for HTTP calls).

**Project Dir:** `Sandbox/snap-and-sell/`

---

## Task Dependency Graph

```
Task 1 (schema) → Task 2 (notifications CRUD) → Task 3 (notifications API) → Task 5 (notifications frontend)
Task 1 (schema) → Task 4 (price comps model + intake) → Task 6 (price comps frontend)
Task 1 (schema) → Task 7 (share links backend) → Task 8 (share links frontend)
```

Tasks 2, 4, 7 can run in parallel after Task 1. Frontend tasks (5, 6, 8) depend on their respective backends.

---

## Task 1: Schema Migration

**Files:**
- Modify: `backend/database.py:8-47`

**Step 1: Write the failing test**

Create `backend/tests/test_schema_migration.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest backend/tests/test_schema_migration.py -v`
Expected: FAIL — `notifications` table doesn't exist, `price_comps`/`share_url` columns missing.

**Step 3: Update schema in database.py**

Add to `SCHEMA_SQL` (after the offers table, before the closing `"""`):

```sql
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    offer_id INTEGER NOT NULL,
    type TEXT NOT NULL DEFAULT 'new_offer',
    sent INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
    FOREIGN KEY (offer_id) REFERENCES offers(id) ON DELETE CASCADE
);
```

Add two columns to the listings CREATE TABLE (after `location TEXT,`):

```sql
    price_comps TEXT,
    share_url TEXT,
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest backend/tests/test_schema_migration.py -v`
Expected: All 7 tests PASS.

**Step 5: Run full test suite**

Run: `python3 -m pytest backend/tests/ -v`
Expected: All 231+ tests PASS (existing tests unaffected by new nullable columns and new table).

**Step 6: Commit**

```bash
git add backend/database.py backend/tests/test_schema_migration.py
git commit -m "feat: add notifications table, price_comps and share_url columns"
```

---

## Task 2: Notifications CRUD

**Files:**
- Modify: `backend/models.py` (add NotificationResponse model + 3 CRUD functions)
- Create: `backend/tests/test_notifications.py`

**Step 1: Write the failing tests**

Create `backend/tests/test_notifications.py`:

```python
"""Tests for notification CRUD operations."""

import os
import tempfile
import pytest
from backend.database import init_db
from backend import models


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


class TestNotificationCreate:
    def test_create_notification(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        nid = models.create_notification(lid, oid, "new_offer", db_path)
        assert nid > 0

    def test_create_returns_incrementing_ids(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid1 = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="A", buyer_phone="1", offer_amount=50),
            db_path,
        )
        oid2 = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="B", buyer_phone="2", offer_amount=60),
            db_path,
        )
        nid1 = models.create_notification(lid, oid1, "new_offer", db_path)
        nid2 = models.create_notification(lid, oid2, "new_offer", db_path)
        assert nid2 > nid1


class TestNotificationList:
    def test_list_pending(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        models.create_notification(lid, oid, "new_offer", db_path)
        pending = models.list_notifications(sent=False, db_path=db_path)
        assert len(pending) == 1
        assert pending[0].sent is False

    def test_list_excludes_sent(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        nid = models.create_notification(lid, oid, "new_offer", db_path)
        models.mark_notification_sent(nid, db_path)
        pending = models.list_notifications(sent=False, db_path=db_path)
        assert len(pending) == 0

    def test_list_all(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        nid = models.create_notification(lid, oid, "new_offer", db_path)
        models.mark_notification_sent(nid, db_path)
        oid2 = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="Y", buyer_phone="666", offer_amount=90),
            db_path,
        )
        models.create_notification(lid, oid2, "new_offer", db_path)
        all_notifs = models.list_notifications(db_path=db_path)
        assert len(all_notifs) == 2

    def test_notification_has_listing_and_offer_info(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Widget", asking_price=100), db_path
        )
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="Alice", buyer_phone="202-555-1234", offer_amount=80),
            db_path,
        )
        models.create_notification(lid, oid, "new_offer", db_path)
        pending = models.list_notifications(sent=False, db_path=db_path)
        n = pending[0]
        assert n.listing_id == lid
        assert n.offer_id == oid
        assert n.type == "new_offer"


class TestNotificationMarkSent:
    def test_mark_sent(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        nid = models.create_notification(lid, oid, "new_offer", db_path)
        result = models.mark_notification_sent(nid, db_path)
        assert result is True

    def test_mark_sent_nonexistent(self, db_path):
        result = models.mark_notification_sent(999, db_path)
        assert result is False

    def test_mark_sent_changes_flag(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        nid = models.create_notification(lid, oid, "new_offer", db_path)
        models.mark_notification_sent(nid, db_path)
        sent = models.list_notifications(sent=True, db_path=db_path)
        assert len(sent) == 1
        assert sent[0].sent is True


class TestNotificationCascadeDelete:
    def test_delete_listing_deletes_notifications(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        models.create_notification(lid, oid, "new_offer", db_path)
        models.delete_listing(lid, db_path)
        all_notifs = models.list_notifications(db_path=db_path)
        assert len(all_notifs) == 0
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest backend/tests/test_notifications.py -v`
Expected: FAIL — `create_notification`, `list_notifications`, `mark_notification_sent` don't exist.

**Step 3: Implement in models.py**

Add `NotificationResponse` model after `PhotoResponse`:

```python
class NotificationResponse(BaseModel):
    id: int
    listing_id: int
    offer_id: int
    type: str
    sent: bool
    created_at: str
```

Add 3 CRUD functions at end of `models.py`:

```python
def create_notification(
    listing_id: int, offer_id: int, notif_type: str = "new_offer",
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    conn = get_connection(db_path)
    cursor = conn.execute(
        "INSERT INTO notifications (listing_id, offer_id, type) VALUES (?, ?, ?)",
        (listing_id, offer_id, notif_type),
    )
    conn.commit()
    nid = cursor.lastrowid
    conn.close()
    return nid


def list_notifications(
    sent: bool | None = None, db_path: str = DEFAULT_DB_PATH
) -> list[NotificationResponse]:
    conn = get_connection(db_path)
    if sent is not None:
        rows = conn.execute(
            "SELECT * FROM notifications WHERE sent = ? ORDER BY created_at DESC",
            (int(sent),),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM notifications ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [NotificationResponse(**{**dict(r), "sent": bool(r["sent"])}) for r in rows]


def mark_notification_sent(
    nid: int, db_path: str = DEFAULT_DB_PATH
) -> bool:
    conn = get_connection(db_path)
    cursor = conn.execute(
        "UPDATE notifications SET sent = 1 WHERE id = ?", (nid,)
    )
    conn.commit()
    changed = cursor.rowcount > 0
    conn.close()
    return changed
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest backend/tests/test_notifications.py -v`
Expected: All 10 tests PASS.

**Step 5: Commit**

```bash
git add backend/models.py backend/tests/test_notifications.py
git commit -m "feat: add notification CRUD (create, list, mark sent)"
```

---

## Task 3: Notifications API Endpoints + Auto-Create on Offer

**Files:**
- Modify: `backend/api.py` (add 2 endpoints + modify `create_offer`)
- Create: `backend/tests/test_notifications_api.py`

**Step 1: Write the failing tests**

Create `backend/tests/test_notifications_api.py`:

```python
"""Tests for notification API endpoints."""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from backend.database import init_db


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


def _make_active_listing(client, title="Widget", asking=100.0, min_price=70.0):
    resp = client.post("/api/listings", json={
        "title": title, "asking_price": asking, "min_price": min_price,
    })
    lid = resp.json()["id"]
    client.post("/api/listings/batch-approve", json={"ids": [lid]})
    return lid


class TestOfferCreatesNotification:
    def test_offer_creates_notification(self, client):
        lid = _make_active_listing(client)
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Alice",
            "buyer_phone": "202-555-1234", "offer_amount": 100,
        })
        resp = client.get("/api/notifications?sent=false")
        assert resp.status_code == 200
        notifs = resp.json()
        assert len(notifs) == 1
        assert notifs[0]["listing_id"] == lid
        assert notifs[0]["type"] == "new_offer"
        assert notifs[0]["sent"] is False

    def test_multiple_offers_create_multiple_notifications(self, client):
        lid = _make_active_listing(client)
        for name in ["Alice", "Bob", "Carol"]:
            client.post("/api/offers", json={
                "listing_id": lid, "buyer_name": name,
                "buyer_phone": "555-0000", "offer_amount": 80,
            })
        resp = client.get("/api/notifications?sent=false")
        assert len(resp.json()) == 3

    def test_rejected_offer_still_creates_notification(self, client):
        lid = _make_active_listing(client)
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Lowball",
            "buyer_phone": "555", "offer_amount": 10,
        })
        resp = client.get("/api/notifications?sent=false")
        assert len(resp.json()) == 1


class TestNotificationEndpoints:
    def test_list_pending(self, client):
        lid = _make_active_listing(client)
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "X",
            "buyer_phone": "555", "offer_amount": 80,
        })
        resp = client.get("/api/notifications?sent=false")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_all(self, client):
        resp = client.get("/api/notifications")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_mark_sent(self, client):
        lid = _make_active_listing(client)
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "X",
            "buyer_phone": "555", "offer_amount": 80,
        })
        notifs = client.get("/api/notifications?sent=false").json()
        nid = notifs[0]["id"]

        resp = client.put(f"/api/notifications/{nid}")
        assert resp.status_code == 200

        # Now pending is empty
        assert len(client.get("/api/notifications?sent=false").json()) == 0
        # But all shows 1 (sent)
        assert len(client.get("/api/notifications").json()) == 1

    def test_mark_sent_nonexistent(self, client):
        resp = client.put("/api/notifications/999")
        assert resp.status_code == 404

    def test_notification_includes_context(self, client):
        """Notification response includes listing title and offer details."""
        lid = _make_active_listing(client, title="Fancy Chair", asking=500)
        client.post("/api/offers", json={
            "listing_id": lid, "buyer_name": "Alice",
            "buyer_phone": "202-555-1234", "offer_amount": 400,
        })
        notifs = client.get("/api/notifications?sent=false").json()
        n = notifs[0]
        assert n["listing_title"] == "Fancy Chair"
        assert n["buyer_name"] == "Alice"
        assert n["offer_amount"] == 400.0
        assert "decision" in n


class TestNotificationCount:
    def test_dashboard_notification_count(self, client):
        """GET /api/notifications/count returns unsent count."""
        lid = _make_active_listing(client)
        for i in range(3):
            client.post("/api/offers", json={
                "listing_id": lid, "buyer_name": f"Buyer{i}",
                "buyer_phone": "555", "offer_amount": 80,
            })
        resp = client.get("/api/notifications/count")
        assert resp.status_code == 200
        assert resp.json()["unsent"] == 3
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest backend/tests/test_notifications_api.py -v`
Expected: FAIL — endpoints don't exist yet, offer doesn't create notification.

**Step 3: Implement API changes**

In `backend/api.py`, add after the meeting spots section:

```python
# --- Notifications ---

@app.get("/api/notifications")
def list_notifications(sent: bool | None = None):
    notifs = models.list_notifications(sent=sent, db_path=_get_db_path())
    result = []
    for n in notifs:
        d = n.model_dump()
        # Enrich with listing and offer context
        listing = models.get_listing(n.listing_id, _get_db_path())
        offers = models.list_offers(listing_id=n.listing_id, db_path=_get_db_path())
        offer = next((o for o in offers if o.id == n.offer_id), None)
        d["listing_title"] = listing.title if listing else None
        d["listing_asking_price"] = listing.asking_price if listing else None
        if offer:
            d["buyer_name"] = offer.buyer_name
            d["buyer_phone"] = offer.buyer_phone
            d["offer_amount"] = offer.offer_amount
            d["decision"] = offer.status
        result.append(d)
    return result


@app.get("/api/notifications/count")
def notification_count():
    pending = models.list_notifications(sent=False, db_path=_get_db_path())
    return {"unsent": len(pending)}


@app.put("/api/notifications/{nid}")
def mark_notification_sent(nid: int):
    ok = models.mark_notification_sent(nid, _get_db_path())
    if not ok:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "marked as sent"}
```

In the `create_offer` function, add notification creation after `models.update_offer_status(...)`:

```python
    models.create_notification(data.listing_id, oid, "new_offer", _get_db_path())
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest backend/tests/test_notifications_api.py -v`
Expected: All 10 tests PASS.

**Step 5: Run full test suite**

Run: `python3 -m pytest backend/tests/ -v`
Expected: All tests PASS. The existing offer tests still work — notification creation is a side effect that doesn't change the offer response (except existing tests that check offer counts may need adjustment if notifications appear in responses).

**Step 6: Commit**

```bash
git add backend/api.py backend/tests/test_notifications_api.py
git commit -m "feat: add notification endpoints, auto-create on new offer"
```

---

## Task 4: Price Comparisons — Model + Intake Integration

**Files:**
- Modify: `backend/models.py:9-50` (add `price_comps` and `share_url` to Pydantic models)
- Modify: `backend/models.py:84-98` (update `create_listing` INSERT to include new columns)
- Create: `backend/tests/test_price_comps.py`

**Step 1: Write the failing tests**

Create `backend/tests/test_price_comps.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest backend/tests/test_price_comps.py -v`
Expected: FAIL — `price_comps` and `share_url` not in Pydantic models.

**Step 3: Update Pydantic models and create_listing**

In `backend/models.py`, add to `ListingCreate` (after `location`):

```python
    price_comps: str | None = None
    share_url: str | None = None
```

Add to `ListingUpdate` (after `location`):

```python
    price_comps: str | None = None
    share_url: str | None = None
```

Add to `ListingResponse` (after `location`):

```python
    price_comps: str | None = None
    share_url: str | None = None
```

Update `create_listing` INSERT to include the new columns:

```python
def create_listing(data: ListingCreate, db_path: str = DEFAULT_DB_PATH) -> int:
    conn = get_connection(db_path)
    cursor = conn.execute(
        """INSERT INTO listings (title, description, category, condition,
           asking_price, min_price, original_price, purchase_date,
           purchase_source, location, price_comps, share_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data.title, data.description, data.category, data.condition,
         data.asking_price, data.min_price, data.original_price,
         data.purchase_date, data.purchase_source, data.location,
         data.price_comps, data.share_url),
    )
    conn.commit()
    lid = cursor.lastrowid
    conn.close()
    return lid
```

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest backend/tests/test_price_comps.py -v`
Expected: All 7 tests PASS.

**Step 5: Run full test suite**

Run: `python3 -m pytest backend/tests/ -v`
Expected: All tests PASS.

**Step 6: Commit**

```bash
git add backend/models.py backend/tests/test_price_comps.py
git commit -m "feat: add price_comps and share_url to listing model"
```

---

## Task 5: Notifications Frontend

**Files:**
- Modify: `frontend/src/components/Dashboard.jsx`

**Step 1: Add notification badge and count**

In `Dashboard.jsx`, add state for notification count:

```javascript
const [notifCount, setNotifCount] = useState(0);
```

Add fetch in the `fetchListings` callback (or a separate useEffect):

```javascript
useEffect(() => {
  const loadNotifs = async () => {
    try {
      const res = await fetch("/api/notifications/count");
      if (res.ok) {
        const data = await res.json();
        setNotifCount(data.unsent);
      }
    } catch {}
  };
  loadNotifs();
}, [allListings]); // refresh when listings change
```

Add a notification badge in the page header, after the subtitle:

```jsx
{notifCount > 0 && (
  <div
    style={{
      marginTop: "var(--space-sm)",
      padding: "var(--space-sm) var(--space-md)",
      background: "rgba(233, 69, 96, 0.15)",
      border: "1px solid rgba(233, 69, 96, 0.3)",
      borderRadius: "var(--radius-md)",
      color: "var(--accent-coral)",
      fontWeight: 700,
      fontSize: "var(--text-base)",
    }}
  >
    {notifCount} new offer{notifCount !== 1 ? "s" : ""} — check your email or run notifications
  </div>
)}
```

**Step 2: Verify visually**

Start backend and frontend, create a listing, approve it, submit an offer. The dashboard should show the notification badge.

**Step 3: Commit**

```bash
git add frontend/src/components/Dashboard.jsx
git commit -m "feat: add notification count badge to dashboard"
```

---

## Task 6: Price Comparisons Frontend

**Files:**
- Modify: `frontend/src/components/ListingCard.jsx`
- Modify: `frontend/src/components/MarketplaceCard.jsx`

**Step 1: Add comps display to ListingCard (Dashboard)**

In `ListingCard.jsx`, after the Category + Condition section (after line 244), add:

```jsx
{/* Price Comparisons */}
{listing.price_comps && (() => {
  try {
    const comps = JSON.parse(listing.price_comps);
    if (comps.length === 0) return null;
    return (
      <div
        style={{
          marginTop: "var(--space-md)",
          padding: "var(--space-sm) var(--space-md)",
          background: "rgba(78, 205, 196, 0.08)",
          borderRadius: "var(--radius-sm)",
          fontSize: "var(--text-sm)",
        }}
      >
        <p style={{ color: "var(--accent-teal)", fontWeight: 700, marginBottom: 4 }}>
          Price Comps
        </p>
        {comps.map((c, i) => (
          <p key={i} style={{ color: "var(--text-secondary)", marginBottom: 2 }}>
            {c.source}: ${Number(c.price).toFixed(0)}
            {c.note && <span style={{ color: "var(--text-muted)" }}> ({c.note})</span>}
          </p>
        ))}
      </div>
    );
  } catch { return null; }
})()}
```

**Step 2: Add comps display to MarketplaceCard**

In `MarketplaceCard.jsx`, after the description paragraph and before the bottom price row, add:

```jsx
{listing.price_comps && (() => {
  try {
    const comps = JSON.parse(listing.price_comps);
    if (comps.length === 0) return null;
    const prices = comps.map(c => c.price).filter(Boolean);
    const min = Math.min(...prices);
    const max = Math.max(...prices);
    return (
      <p style={{
        fontSize: "14px",
        color: "var(--text-muted)",
        marginBottom: "var(--space-sm)",
      }}>
        Similar: ${min.toFixed(0)}–${max.toFixed(0)}
      </p>
    );
  } catch { return null; }
})()}
```

**Step 3: Verify visually**

Create a listing with `price_comps` JSON via curl, approve it. Check both Dashboard and Marketplace display.

**Step 4: Commit**

```bash
git add frontend/src/components/ListingCard.jsx frontend/src/components/MarketplaceCard.jsx
git commit -m "feat: display price comparisons on listing and marketplace cards"
```

---

## Task 7: Share Links Backend (Rebrandly API)

**Files:**
- Create: `backend/share.py`
- Create: `backend/tests/test_share.py`
- Modify: `backend/api.py` (add share endpoint)
- Modify: `.env` (add `REBRANDLY_API_KEY`)
- Modify: `requirements.txt` — no change needed (`urllib.request` is stdlib)

**Step 1: Write the failing tests**

Create `backend/tests/test_share.py`:

```python
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
```

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest backend/tests/test_share.py -v`
Expected: FAIL — `backend.share` module doesn't exist.

**Step 3: Implement share.py**

Create `backend/share.py`:

```python
"""Rebrandly share link generation."""
from __future__ import annotations
import json
import os
import re
import urllib.request


REBRANDLY_API_KEY = os.environ.get("REBRANDLY_API_KEY", "")
REBRANDLY_DOMAIN = "karthik.link"
REBRANDLY_API_URL = "https://api.rebrandly.com/v1/links"


def generate_slashtag(title: str) -> str:
    """Generate a URL-safe slashtag from a listing title."""
    if not title.strip():
        import random
        return f"item-{random.randint(1000, 9999)}"
    slug = title.lower()
    slug = re.sub(r"[\"'()\[\]{}]", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:50]


def _call_rebrandly(payload: dict) -> dict:
    """Make a POST request to Rebrandly API."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        REBRANDLY_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "apikey": REBRANDLY_API_KEY,
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def create_short_link(
    title: str, listing_id: int, base_url: str = "http://localhost:5173"
) -> str | None:
    """Create a Rebrandly short link for a listing. Returns URL or None on failure."""
    payload = {
        "destination": f"{base_url}/?item={listing_id}",
        "slashtag": generate_slashtag(title),
        "domain": {"fullName": REBRANDLY_DOMAIN},
    }
    try:
        result = _call_rebrandly(payload)
        return result.get("shortUrl") or f"https://{REBRANDLY_DOMAIN}/{result.get('slashtag', '')}"
    except Exception:
        return None
```

**Step 4: Add share endpoint to api.py**

In `backend/api.py`, add after the notifications section:

```python
# --- Share Links ---

@app.post("/api/listings/{lid}/share")
def share_listing(lid: int):
    from backend.share import create_short_link

    listing = models.get_listing(lid, _get_db_path())
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Return existing share URL if already generated
    if listing.share_url:
        return {"share_url": listing.share_url}

    url = create_short_link(listing.title, lid)
    if url is None:
        raise HTTPException(status_code=502, detail="Rebrandly API failed to create link")

    models.update_listing(lid, models.ListingUpdate(share_url=url), _get_db_path())
    return {"share_url": url}
```

**Step 5: Add REBRANDLY_API_KEY to .env**

Append to `.env`:

```
REBRANDLY_API_KEY=your_api_key_here
```

Note: The actual API key should be obtained from the Rebrandly dashboard (personal account). The tests use mocks so the key isn't needed for testing.

**Step 6: Run test to verify it passes**

Run: `python3 -m pytest backend/tests/test_share.py -v`
Expected: All 10 tests PASS.

**Step 7: Run full test suite**

Run: `python3 -m pytest backend/tests/ -v`
Expected: All tests PASS.

**Step 8: Commit**

```bash
git add backend/share.py backend/tests/test_share.py backend/api.py
git commit -m "feat: add Rebrandly share link generation"
```

---

## Task 8: Share Links Frontend

**Files:**
- Modify: `frontend/src/components/ListingCard.jsx`

**Step 1: Add share button to active listings**

In `ListingCard.jsx`, add state for share status:

```javascript
const [shareUrl, setShareUrl] = useState(listing.share_url || null);
const [sharing, setSharing] = useState(false);
const [copied, setCopied] = useState(false);
```

Add the share handler:

```javascript
const handleShare = async (e) => {
  e.stopPropagation();
  if (shareUrl) {
    navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    return;
  }
  setSharing(true);
  try {
    const res = await fetch(`/api/listings/${listing.id}/share`, { method: "POST" });
    if (res.ok) {
      const data = await res.json();
      setShareUrl(data.share_url);
      navigator.clipboard.writeText(data.share_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  } catch {}
  setSharing(false);
};
```

Add the share button after the Category + Condition section (and after price comps if present), only for active listings:

```jsx
{listing.status === "active" && (
  <div style={{ marginTop: "var(--space-md)" }}>
    <button
      className="btn btn-ghost"
      onClick={handleShare}
      disabled={sharing}
      style={{ width: "100%", fontSize: "var(--text-sm)" }}
    >
      {copied ? "Copied!" : sharing ? "Creating link..." : shareUrl ? `Share: ${shareUrl}` : "Generate Share Link"}
    </button>
  </div>
)}
```

**Step 2: Verify visually**

Start backend and frontend. Create and approve a listing. On the active tab, click the share button. It should generate a link (or show an error if no API key). The second click copies the URL.

**Step 3: Commit**

```bash
git add frontend/src/components/ListingCard.jsx
git commit -m "feat: add share link button to active listings"
```

---

## Task 9: Final Integration + CONTEXT.md Update

**Step 1: Run full test suite**

Run: `python3 -m pytest backend/tests/ -v`
Expected: All tests PASS (should be ~270+ total).

**Step 2: Update CONTEXT.md**

Update `Sandbox/snap-and-sell/.claude/CONTEXT.md`:
- Update endpoint table with new endpoints
- Update test count
- Move implemented features from "Remaining" to "Implemented"
- Add note about REBRANDLY_API_KEY in .env

**Step 3: Commit and push**

```bash
git add .claude/CONTEXT.md
git commit -m "docs: update CONTEXT.md with round 2 features"
env -u GH_TOKEN git push origin main
```
