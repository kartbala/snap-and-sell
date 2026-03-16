# Liquidation Command Center Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Snap & Sell from a local MVP into a deployed household liquidation tool with countdown pricing, email notifications, end-of-life management, and cross-posting to Craigslist/FB Marketplace.

**Architecture:** Build on existing FastAPI + React + SQLite stack. Add `pricing.py` module for countdown computation, `external_posts` table for cross-posting state, email notification triggers via Google Workspace MCP. Deploy as a single service on Render (Railway fallback) with FastAPI serving the React static build.

**Tech Stack:** Python 3.11, FastAPI, SQLite, React 19, Vite 6, Google Workspace MCP, Claude-in-Chrome

**Spec:** `docs/superpowers/specs/2026-03-15-liquidation-command-center-design.md`

---

## File Structure

### New files
| File | Responsibility |
|------|---------------|
| `backend/pricing.py` | Countdown price computation (aggressive, fire_sale, hold strategies) |
| `backend/external_posts.py` | External posts CRUD (Craigslist/FB listing tracking) |
| `backend/email_notify.py` | Email notification composition + sending via Google Workspace MCP |
| `backend/tests/test_pricing.py` | Tests for countdown pricing logic |
| `backend/tests/test_external_posts.py` | Tests for external posts CRUD |
| `backend/tests/test_email_notify.py` | Tests for email composition (send is mocked) |
| `backend/tests/test_end_of_life.py` | Tests for donate/store status transitions |
| `Dockerfile` | Container for Render deployment |
| `render.yaml` | Render service config |

### Modified files
| File | Changes |
|------|---------|
| `backend/database.py` | Add `deadline`, `pricing_strategy`, `pickup_type` columns; create `external_posts` table; migration logic |
| `backend/models.py` | Add new fields to Pydantic models; external posts models + CRUD |
| `backend/api.py` | Replace 30-day expiration with deadline; add `current_price` to marketplace; pass `current_price` to negotiation; new endpoints for external posts and end-of-life |
| `backend/share.py` | Use `BASE_URL` env var instead of hardcoded localhost |
| `backend/tests/test_expiration.py` | Rewrite for deadline-based model |
| `frontend/src/components/Dashboard.jsx` | Add donate/store tabs, end-of-life tab, pickup_type display |
| `frontend/src/components/Marketplace.jsx` | Show `current_price` with original price strikethrough |
| `frontend/src/components/MarketplaceCard.jsx` | Display countdown price + urgency |
| `frontend/src/components/ListingCard.jsx` | Add pickup_type + pricing_strategy editing |
| `frontend/src/App.jsx` | No changes needed (routing stays the same) |
| `frontend/vite.config.js` | No changes (proxy config stays for dev) |

---

## Chunk 1: Backend Core — Schema Migration + Pricing Engine

### Task 1: Schema Migration

**Files:**
- Modify: `backend/database.py:1-66`
- Test: `backend/tests/test_schema_migration.py` (existing, will extend)

- [ ] **Step 1: Write failing test for new columns**

```python
# In backend/tests/test_schema_migration.py — add these tests

def test_listings_has_deadline_column(db_path):
    conn = sqlite3.connect(db_path)
    row = conn.execute("PRAGMA table_info(listings)").fetchall()
    columns = [r[1] for r in row]
    conn.close()
    assert "deadline" in columns

def test_listings_has_pricing_strategy_column(db_path):
    conn = sqlite3.connect(db_path)
    row = conn.execute("PRAGMA table_info(listings)").fetchall()
    columns = [r[1] for r in row]
    conn.close()
    assert "pricing_strategy" in columns

def test_listings_has_pickup_type_column(db_path):
    conn = sqlite3.connect(db_path)
    row = conn.execute("PRAGMA table_info(listings)").fetchall()
    columns = [r[1] for r in row]
    conn.close()
    assert "pickup_type" in columns

def test_external_posts_table_exists(db_path):
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='external_posts'"
    ).fetchone()
    conn.close()
    assert row is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest backend/tests/test_schema_migration.py -v -k "deadline or pricing_strategy or pickup_type or external_posts_table"`
Expected: FAIL — columns and table don't exist yet

- [ ] **Step 3: Add new columns and external_posts table to SCHEMA_SQL**

In `backend/database.py`, update `SCHEMA_SQL` to add the three new columns to the `listings` CREATE TABLE and add the `external_posts` CREATE TABLE:

```python
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
    price_comps TEXT,
    share_url TEXT,
    deadline TEXT DEFAULT '2026-06-01',
    pricing_strategy TEXT DEFAULT 'aggressive',
    pickup_type TEXT DEFAULT 'meeting_spot',
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

CREATE TABLE IF NOT EXISTS external_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,
    platform TEXT NOT NULL,
    url TEXT,
    posted_at TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'active',
    last_price_posted REAL,
    FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE
);
"""
```

Also add a migration function for existing databases:

```python
MIGRATIONS = [
    "ALTER TABLE listings ADD COLUMN deadline TEXT DEFAULT '2026-06-01'",
    "ALTER TABLE listings ADD COLUMN pricing_strategy TEXT DEFAULT 'aggressive'",
    "ALTER TABLE listings ADD COLUMN pickup_type TEXT DEFAULT 'meeting_spot'",
]

def migrate_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Apply migrations for existing databases. Safe to run multiple times."""
    conn = sqlite3.connect(db_path)
    for sql in MIGRATIONS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # Column already exists
    conn.commit()
    conn.close()
```

Update `init_db` to call `migrate_db` after `executescript`:

```python
def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.close()
    migrate_db(db_path)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_schema_migration.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite to check nothing broke**

Run: `python3 -m pytest backend/tests/ -v`
Expected: All existing tests still pass (new columns have defaults, so no breakage)

- [ ] **Step 6: Commit**

```bash
git add backend/database.py backend/tests/test_schema_migration.py
git commit -m "feat: add deadline, pricing_strategy, pickup_type columns and external_posts table"
```

---

### Task 2: Pydantic Model Updates

**Files:**
- Modify: `backend/models.py:1-95`

- [ ] **Step 1: Add new fields to ListingCreate, ListingUpdate, and ListingResponse**

In `backend/models.py`:

`ListingCreate` — add after `share_url`:
```python
    deadline: str | None = None
    pricing_strategy: str | None = None
    pickup_type: str | None = None
```

`ListingUpdate` — add after `share_url`:
```python
    deadline: str | None = None
    pricing_strategy: str | None = None
    pickup_type: str | None = None
```

`ListingResponse` — add after `share_url`:
```python
    deadline: str | None = None
    pricing_strategy: str | None = None
    pickup_type: str | None = None
```

- [ ] **Step 2: Update create_listing SQL to include new columns**

In `backend/models.py`, update the `create_listing` function's INSERT statement to include the three new columns:

```python
def create_listing(data: ListingCreate, db_path: str = DEFAULT_DB_PATH) -> int:
    conn = get_connection(db_path)
    cursor = conn.execute(
        """INSERT INTO listings (title, description, category, condition,
           asking_price, min_price, original_price, purchase_date,
           purchase_source, location, price_comps, share_url,
           deadline, pricing_strategy, pickup_type)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data.title, data.description, data.category, data.condition,
         data.asking_price, data.min_price, data.original_price,
         data.purchase_date, data.purchase_source, data.location,
         data.price_comps, data.share_url,
         data.deadline, data.pricing_strategy, data.pickup_type),
    )
    conn.commit()
    lid = cursor.lastrowid
    conn.close()
    return lid
```

- [ ] **Step 3: Run existing tests to verify nothing broke**

Run: `python3 -m pytest backend/tests/ -v`
Expected: ALL PASS (new fields are optional with defaults)

- [ ] **Step 4: Commit**

```bash
git add backend/models.py
git commit -m "feat: add deadline, pricing_strategy, pickup_type to Pydantic models and create_listing"
```

---

### Task 3: Pricing Engine

**Files:**
- Create: `backend/pricing.py`
- Create: `backend/tests/test_pricing.py`

- [ ] **Step 1: Write failing tests for all three strategies**

Create `backend/tests/test_pricing.py`:

```python
"""Tests for countdown pricing engine."""
import pytest
from datetime import date, timedelta
from backend.pricing import compute_current_price


class TestHoldStrategy:
    def test_hold_never_drops(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="hold",
            deadline=date.today() + timedelta(days=1),
        )
        assert result == 100.0

    def test_hold_even_past_deadline(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="hold",
            deadline=date.today() - timedelta(days=5),
        )
        assert result == 100.0


class TestAggressiveStrategy:
    def test_4_plus_weeks_no_discount(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=30),
        )
        assert result == 100.0

    def test_3_weeks_10_percent_off(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=18),
        )
        assert result == 90.0

    def test_2_weeks_20_percent_off(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=11),
        )
        assert result == 80.0

    def test_1_week_35_percent_off(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=5),
        )
        assert result == 65.0

    def test_last_3_days_50_percent_off(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=2),
        )
        assert result == 50.0

    def test_never_below_min_price(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=70.0,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=2),
        )
        assert result == 70.0  # 50% off = 50, but min_price = 70

    def test_no_min_price_drops_fully(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=None,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=2),
        )
        assert result == 50.0


class TestFireSaleStrategy:
    def test_14_days_out_no_discount(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=None,
            pricing_strategy="fire_sale",
            deadline=date.today() + timedelta(days=15),
        )
        assert result == 100.0

    def test_13_days_out_5_percent_off(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=None,
            pricing_strategy="fire_sale",
            deadline=date.today() + timedelta(days=13),
        )
        assert result == 95.0

    def test_7_days_out_35_percent_off(self):
        # 14 - 7 = 7 days into fire sale, 7 * 5% = 35%
        result = compute_current_price(
            asking_price=100.0,
            min_price=None,
            pricing_strategy="fire_sale",
            deadline=date.today() + timedelta(days=7),
        )
        assert result == 65.0

    def test_max_70_percent_off(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=None,
            pricing_strategy="fire_sale",
            deadline=date.today(),
        )
        assert result == 30.0  # 14 * 5% = 70% off, so 30

    def test_respects_min_price(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=80.0,
            pricing_strategy="fire_sale",
            deadline=date.today() + timedelta(days=7),
        )
        assert result == 80.0  # 35% off = 65, but min = 80


class TestEdgeCases:
    def test_no_asking_price_returns_none(self):
        result = compute_current_price(
            asking_price=None,
            min_price=None,
            pricing_strategy="aggressive",
            deadline=date.today() + timedelta(days=10),
        )
        assert result is None

    def test_past_deadline_uses_max_discount(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=None,
            pricing_strategy="aggressive",
            deadline=date.today() - timedelta(days=5),
        )
        assert result == 50.0  # Max aggressive discount

    def test_unknown_strategy_treated_as_hold(self):
        result = compute_current_price(
            asking_price=100.0,
            min_price=50.0,
            pricing_strategy="unknown",
            deadline=date.today() + timedelta(days=2),
        )
        assert result == 100.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest backend/tests/test_pricing.py -v`
Expected: FAIL — `backend.pricing` module doesn't exist

- [ ] **Step 3: Implement pricing.py**

Create `backend/pricing.py`:

```python
"""Countdown pricing engine for liquidation deadlines."""
from __future__ import annotations
from datetime import date


def compute_current_price(
    asking_price: float | None,
    min_price: float | None,
    pricing_strategy: str,
    deadline: date,
) -> float | None:
    """Compute the current discounted price based on strategy and deadline.

    Returns None if asking_price is None.
    Never drops below min_price (if set).
    """
    if asking_price is None:
        return None

    days_left = (deadline - date.today()).days

    if pricing_strategy == "aggressive":
        discount = _aggressive_discount(days_left)
    elif pricing_strategy == "fire_sale":
        discount = _fire_sale_discount(days_left)
    else:
        # "hold" or unknown — no discount
        discount = 0.0

    discounted = asking_price * (1 - discount)

    if min_price is not None:
        discounted = max(discounted, min_price)

    return round(discounted, 2)


def _aggressive_discount(days_left: int) -> float:
    """Stepped discount schedule."""
    if days_left >= 28:
        return 0.0
    if days_left >= 21:
        return 0.10
    if days_left >= 14:
        return 0.20
    if days_left >= 7:
        return 0.35
    # Last 3 days or fewer (and anything < 7 days)
    return 0.50


def _fire_sale_discount(days_left: int) -> float:
    """5% per day for last 14 days, max 70%."""
    if days_left >= 14:
        return 0.0
    days_into_sale = 14 - max(days_left, 0)
    return min(days_into_sale * 0.05, 0.70)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_pricing.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/pricing.py backend/tests/test_pricing.py
git commit -m "feat: add countdown pricing engine with aggressive, fire_sale, hold strategies"
```

---

### Task 4: Update Marketplace API — Deadline-Based Filtering + Current Price

**Files:**
- Modify: `backend/api.py:14,99-126`
- Rewrite: `backend/tests/test_expiration.py`

- [ ] **Step 1: Rewrite test_expiration.py for deadline model**

Replace the contents of `backend/tests/test_expiration.py` with:

```python
"""Tests for deadline-based marketplace filtering and pricing."""
import sqlite3
import pytest
from datetime import date, timedelta, datetime
from backend.database import init_db
from backend.models import ListingCreate, create_listing, update_listing, ListingUpdate

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

def _create_listing(db_path, deadline, status="active", asking_price=100.0, min_price=70.0, pricing_strategy="aggressive"):
    lid = create_listing(
        ListingCreate(title="Test Item", asking_price=asking_price, min_price=min_price),
        db_path,
    )
    update_listing(lid, ListingUpdate(status=status, deadline=deadline, pricing_strategy=pricing_strategy), db_path)
    return lid


class TestDeadlineFiltering:
    def test_active_before_deadline_shows_in_marketplace(self, client, db_path):
        deadline = (date.today() + timedelta(days=30)).isoformat()
        _create_listing(db_path, deadline)
        res = client.get("/api/marketplace")
        assert res.status_code == 200
        assert len(res.json()) == 1

    def test_past_deadline_hidden_from_marketplace(self, client, db_path):
        deadline = (date.today() - timedelta(days=1)).isoformat()
        _create_listing(db_path, deadline)
        res = client.get("/api/marketplace")
        assert res.status_code == 200
        assert len(res.json()) == 0

    def test_draft_not_in_marketplace(self, client, db_path):
        deadline = (date.today() + timedelta(days=30)).isoformat()
        _create_listing(db_path, deadline, status="draft")
        res = client.get("/api/marketplace")
        assert len(res.json()) == 0

    def test_days_remaining_computed(self, client, db_path):
        deadline = (date.today() + timedelta(days=10)).isoformat()
        _create_listing(db_path, deadline)
        res = client.get("/api/marketplace")
        item = res.json()[0]
        assert item["days_remaining"] == 10


class TestCurrentPriceInMarketplace:
    def test_current_price_included(self, client, db_path):
        deadline = (date.today() + timedelta(days=30)).isoformat()
        _create_listing(db_path, deadline)
        res = client.get("/api/marketplace")
        item = res.json()[0]
        assert "current_price" in item

    def test_current_price_no_discount_far_deadline(self, client, db_path):
        deadline = (date.today() + timedelta(days=30)).isoformat()
        _create_listing(db_path, deadline, asking_price=100.0)
        item = client.get("/api/marketplace").json()[0]
        assert item["current_price"] == 100.0

    def test_current_price_discounted_near_deadline(self, client, db_path):
        deadline = (date.today() + timedelta(days=5)).isoformat()
        _create_listing(db_path, deadline, asking_price=100.0, min_price=50.0)
        item = client.get("/api/marketplace").json()[0]
        assert item["current_price"] == 65.0  # aggressive, 1 week = 35% off

    def test_hold_strategy_no_discount(self, client, db_path):
        deadline = (date.today() + timedelta(days=2)).isoformat()
        _create_listing(db_path, deadline, pricing_strategy="hold")
        item = client.get("/api/marketplace").json()[0]
        assert item["current_price"] == 100.0

    def test_min_price_not_exposed(self, client, db_path):
        deadline = (date.today() + timedelta(days=30)).isoformat()
        _create_listing(db_path, deadline)
        item = client.get("/api/marketplace").json()[0]
        assert "min_price" not in item

    def test_original_asking_price_included(self, client, db_path):
        deadline = (date.today() + timedelta(days=5)).isoformat()
        _create_listing(db_path, deadline, asking_price=100.0)
        item = client.get("/api/marketplace").json()[0]
        assert item["asking_price"] == 100.0  # original preserved
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest backend/tests/test_expiration.py -v`
Expected: FAIL — marketplace still uses old 30-day logic, no `current_price` field

- [ ] **Step 3: Update api.py marketplace endpoint**

In `backend/api.py`:

Remove `LISTING_EXPIRY_DAYS = 30` (line 14).

Replace `_days_remaining` function (lines 99-107) with:

```python
def _days_remaining(deadline: str | None) -> int:
    """Calculate days remaining before a listing's deadline."""
    if not deadline:
        return 0
    try:
        dl = date.fromisoformat(deadline)
    except ValueError:
        return 0
    return max((dl - date.today()).days, 0)
```

Add import at top of file:
```python
from datetime import datetime, date
from backend.pricing import compute_current_price
```
(Replace the existing `from datetime import datetime, timedelta` import.)

Replace the `marketplace()` function (lines 110-126) with:

```python
@app.get("/api/marketplace")
def marketplace():
    listings = models.list_listings(status="active", db_path=_get_db_path())
    today = date.today()
    result = []
    for listing in listings:
        # Skip past-deadline listings
        if listing.deadline:
            try:
                dl = date.fromisoformat(listing.deadline)
            except ValueError:
                continue
            if dl < today:
                continue

        d = listing.model_dump()
        d.pop("min_price", None)
        d["days_remaining"] = _days_remaining(listing.deadline)
        d["current_price"] = compute_current_price(
            asking_price=listing.asking_price,
            min_price=listing.min_price,
            pricing_strategy=listing.pricing_strategy or "aggressive",
            deadline=date.fromisoformat(listing.deadline) if listing.deadline else today,
        )
        result.append(d)
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_expiration.py -v`
Expected: ALL PASS

- [ ] **Step 5: Run full test suite**

Run: `python3 -m pytest backend/tests/ -v`
Expected: All pass. Some existing marketplace tests may need minor fixups if they rely on the old `LISTING_EXPIRY_DAYS` or `timedelta` import.

- [ ] **Step 6: Commit**

```bash
git add backend/api.py backend/tests/test_expiration.py
git commit -m "feat: replace 30-day expiration with deadline-based filtering and current_price"
```

---

### Task 5: Update Offers API — Current Price Pass-Through to Negotiation

**Files:**
- Modify: `backend/api.py:138-159`
- Test: `backend/tests/test_api.py` (add test)

- [ ] **Step 1: Write failing test**

Add to `backend/tests/test_api.py` (or a new test file if cleaner):

```python
def test_offer_uses_current_price_for_negotiation(client, db_path):
    """When deadline is near, current_price is lower — offer at current_price should be accepted."""
    from backend.models import create_listing, update_listing, ListingCreate, ListingUpdate
    from datetime import date, timedelta

    lid = create_listing(
        ListingCreate(title="Discounted Item", asking_price=100.0, min_price=50.0),
        db_path,
    )
    # Set deadline to 5 days out — aggressive = 35% off = $65 current price
    deadline = (date.today() + timedelta(days=5)).isoformat()
    update_listing(lid, ListingUpdate(status="active", deadline=deadline), db_path)

    # Offer $65 — should be accepted (>= min_price of $50)
    res = client.post("/api/offers", json={
        "listing_id": lid,
        "buyer_name": "Test Buyer",
        "buyer_phone": "555-1234",
        "offer_amount": 65.0,
    })
    assert res.status_code == 201
    assert res.json()["decision"] == "accepted"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest backend/tests/test_api.py -v -k "current_price"`
Expected: FAIL or PASS depending on existing logic. If `asking_price=100` and offer=65, it may already go to `min_price` path. Verify behavior.

- [ ] **Step 3: Update create_offer endpoint to pass current_price**

In `backend/api.py`, modify the `create_offer` function:

```python
@app.post("/api/offers", status_code=201)
def create_offer(data: models.OfferCreate):
    from backend.negotiation import evaluate_offer

    listing = models.get_listing(data.listing_id, _get_db_path())
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Compute current (potentially discounted) price
    current_price = compute_current_price(
        asking_price=listing.asking_price,
        min_price=listing.min_price,
        pricing_strategy=listing.pricing_strategy or "aggressive",
        deadline=date.fromisoformat(listing.deadline) if listing.deadline else date.today(),
    )

    oid = models.create_offer(data, _get_db_path())
    result = evaluate_offer(data.offer_amount, current_price, listing.min_price)
    models.update_offer_status(oid, result.decision, result.message, _get_db_path())
    models.create_notification(data.listing_id, oid, "new_offer", _get_db_path())
    response = {
        "offer_id": oid,
        "decision": result.decision,
        "message": result.message,
        "counter_amount": result.counter_amount,
    }
    if result.decision == "accepted":
        spot = suggest_spot(neighborhood=listing.location)
        response["meeting_spot"] = spot_to_dict(spot)
    return response
```

Also update the rejection message in `backend/negotiation.py` line 42 to say "current price" instead of "asking price" (since we're now passing the discounted price):

```python
    if asking_price is not None:
        msg = f"Offer too low. The current price is ${asking_price:,.2f}."
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest backend/tests/ -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/api.py backend/tests/test_api.py
git commit -m "feat: pass current_price to negotiation engine for deadline-aware offers"
```

---

### Task 6: Update share.py — BASE_URL Environment Variable

**Files:**
- Modify: `backend/share.py:42-43`

- [ ] **Step 1: Update create_short_link to use BASE_URL env var**

In `backend/share.py`, change the function signature:

```python
def create_short_link(
    title: str, listing_id: int,
    base_url: str = os.environ.get("BASE_URL", "http://localhost:5173"),
) -> str | None:
```

- [ ] **Step 2: Run share tests**

Run: `python3 -m pytest backend/tests/test_share.py -v`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git add backend/share.py
git commit -m "feat: use BASE_URL env var for share links instead of hardcoded localhost"
```

---

## Chunk 2: End-of-Life + External Posts + Email Notifications

### Task 7: Donate/Store Status Transitions

**Files:**
- Create: `backend/tests/test_end_of_life.py`
- Modify: `backend/api.py` (add batch status endpoint)

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_end_of_life.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest backend/tests/test_end_of_life.py -v`
Expected: FAIL on `batch-status` endpoint (doesn't exist yet). Status transitions should already work since `status` is just a text field.

- [ ] **Step 3: Add batch-status endpoint to api.py**

In `backend/api.py`, add after the `batch_approve` endpoint:

```python
class BatchStatusRequest(BaseModel):
    ids: list[int]
    status: str

@app.post("/api/listings/batch-status")
def batch_status(req: BatchStatusRequest):
    count = models.batch_update_status(req.ids, req.status, _get_db_path())
    return {"updated": count}
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest backend/tests/test_end_of_life.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_end_of_life.py backend/api.py
git commit -m "feat: add donate/store statuses and batch-status endpoint"
```

---

### Task 8: External Posts CRUD

**Files:**
- Create: `backend/external_posts.py`
- Create: `backend/tests/test_external_posts.py`
- Modify: `backend/api.py` (add endpoints)

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_external_posts.py`:

```python
"""Tests for external posts CRUD."""
import pytest
from backend.database import init_db
from backend.models import ListingCreate, create_listing
from backend.external_posts import (
    create_external_post, list_external_posts,
    update_external_post_status, get_stale_posts,
)

@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path

@pytest.fixture
def listing_ids(db_path):
    """Create two listings to satisfy foreign key constraints."""
    lid1 = create_listing(ListingCreate(title="Item A", asking_price=50.0), db_path)
    lid2 = create_listing(ListingCreate(title="Item B", asking_price=80.0), db_path)
    return lid1, lid2


def test_create_and_list(db_path, listing_ids):
    lid1, _ = listing_ids
    pid = create_external_post(
        listing_id=lid1, platform="craigslist",
        url="https://craigslist.org/123", last_price_posted=50.0,
        db_path=db_path,
    )
    assert pid > 0
    posts = list_external_posts(listing_id=lid1, db_path=db_path)
    assert len(posts) == 1
    assert posts[0]["platform"] == "craigslist"
    assert posts[0]["status"] == "active"


def test_update_status(db_path, listing_ids):
    lid1, _ = listing_ids
    pid = create_external_post(listing_id=lid1, platform="facebook", db_path=db_path)
    update_external_post_status(pid, "price_stale", db_path=db_path)
    posts = list_external_posts(listing_id=lid1, db_path=db_path)
    assert posts[0]["status"] == "price_stale"


def test_get_stale_posts(db_path, listing_ids):
    lid1, lid2 = listing_ids
    pid1 = create_external_post(listing_id=lid1, platform="craigslist", db_path=db_path)
    pid2 = create_external_post(listing_id=lid2, platform="facebook", db_path=db_path)
    update_external_post_status(pid1, "price_stale", db_path=db_path)
    stale = get_stale_posts(db_path=db_path)
    assert len(stale) == 1
    assert stale[0]["id"] == pid1


def test_list_by_platform(db_path, listing_ids):
    lid1, _ = listing_ids
    create_external_post(listing_id=lid1, platform="craigslist", db_path=db_path)
    create_external_post(listing_id=lid1, platform="facebook", db_path=db_path)
    cl = list_external_posts(listing_id=lid1, platform="craigslist", db_path=db_path)
    assert len(cl) == 1
    assert cl[0]["platform"] == "craigslist"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest backend/tests/test_external_posts.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement external_posts.py**

Create `backend/external_posts.py`:

```python
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
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest backend/tests/test_external_posts.py -v`
Expected: ALL PASS

- [ ] **Step 5: Add API endpoints for external posts**

In `backend/api.py`, add at the end:

```python
# --- External Posts ---

@app.get("/api/listings/{lid}/external-posts")
def list_external_posts_for_listing(lid: int):
    from backend.external_posts import list_external_posts
    listing = models.get_listing(lid, _get_db_path())
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return list_external_posts(listing_id=lid, db_path=_get_db_path())

@app.get("/api/external-posts/stale")
def get_stale_external_posts():
    from backend.external_posts import get_stale_posts
    return get_stale_posts(db_path=_get_db_path())
```

- [ ] **Step 6: Run full test suite**

Run: `python3 -m pytest backend/tests/ -v`
Expected: ALL PASS

- [ ] **Step 7: Commit**

```bash
git add backend/external_posts.py backend/tests/test_external_posts.py backend/api.py
git commit -m "feat: add external posts CRUD and API endpoints for cross-posting tracking"
```

---

### Task 9: Email Notification Module

**Files:**
- Create: `backend/email_notify.py`
- Create: `backend/tests/test_email_notify.py`

This module composes email content. Actual sending is done via Google Workspace MCP during Claude Code sessions — the module just prepares the data.

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_email_notify.py`:

```python
"""Tests for email notification composition."""
import pytest
from backend.email_notify import compose_seller_notification, compose_buyer_acceptance


def test_seller_notification_contains_item_title():
    email = compose_seller_notification(
        listing_title="IKEA KALLAX",
        buyer_name="Jane",
        offer_amount=80.0,
        decision="accepted",
        dashboard_url="https://sell.example.com/dashboard",
    )
    assert "IKEA KALLAX" in email["subject"]
    assert "Jane" in email["body"]
    assert "$80.00" in email["body"]
    assert "accepted" in email["body"].lower()


def test_seller_notification_has_correct_to():
    email = compose_seller_notification(
        listing_title="Chair",
        buyer_name="Bob",
        offer_amount=50.0,
        decision="rejected",
        notification_email="karthik@balasubramanian.us",
    )
    assert email["to"] == "karthik@balasubramanian.us"


def test_buyer_acceptance_meeting_spot():
    email = compose_buyer_acceptance(
        listing_title="Desk",
        offer_amount=120.0,
        buyer_email="buyer@example.com",
        pickup_type="meeting_spot",
        pickup_details="Tenleytown Metro Station",
        contact_number="+1-202-684-6252",
    )
    assert email["to"] == "buyer@example.com"
    assert "Desk" in email["subject"]
    assert "Tenleytown" in email["body"]
    assert "+1-202-684-6252" in email["body"]


def test_buyer_acceptance_home_pickup():
    email = compose_buyer_acceptance(
        listing_title="Couch",
        offer_amount=200.0,
        buyer_email="buyer@example.com",
        pickup_type="home",
        pickup_details="123 Main St, Washington DC",
        contact_number="+1-202-684-6252",
    )
    assert "123 Main St" in email["body"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest backend/tests/test_email_notify.py -v`
Expected: FAIL — module doesn't exist

- [ ] **Step 3: Implement email_notify.py**

Create `backend/email_notify.py`:

```python
"""Email notification composition for Snap & Sell.

Composes email dicts (to, subject, body) that can be sent via
Google Workspace MCP's send_gmail_message tool during Claude Code sessions.
"""
from __future__ import annotations
import os

DEFAULT_NOTIFICATION_EMAIL = os.environ.get(
    "NOTIFICATION_EMAIL", "karthik@balasubramanian.us"
)
DEFAULT_CONTACT_NUMBER = os.environ.get(
    "GOOGLE_VOICE_NUMBER", "+1-202-684-6252"
)


def compose_seller_notification(
    listing_title: str,
    buyer_name: str,
    offer_amount: float,
    decision: str,
    dashboard_url: str = "",
    notification_email: str = DEFAULT_NOTIFICATION_EMAIL,
) -> dict:
    """Compose an email to the seller about a new offer."""
    subject = f"Snap & Sell: New offer on {listing_title} — {decision}"
    body = (
        f"New offer received:\n\n"
        f"Item: {listing_title}\n"
        f"Buyer: {buyer_name}\n"
        f"Offer: ${offer_amount:,.2f}\n"
        f"Decision: {decision}\n"
    )
    if dashboard_url:
        body += f"\nReview in dashboard: {dashboard_url}\n"
    return {"to": notification_email, "subject": subject, "body": body}


def compose_buyer_acceptance(
    listing_title: str,
    offer_amount: float,
    buyer_email: str,
    pickup_type: str,
    pickup_details: str,
    contact_number: str = DEFAULT_CONTACT_NUMBER,
) -> dict:
    """Compose an email to the buyer that their offer was accepted."""
    subject = f"Your offer on {listing_title} was accepted!"
    body = (
        f"Great news! Your offer of ${offer_amount:,.2f} for {listing_title} has been accepted.\n\n"
        f"Pickup: {pickup_details}\n"
        f"Contact Karthik at {contact_number} to arrange a time.\n"
    )
    if pickup_type == "home":
        body += "\nPlease text or call to confirm a pickup window.\n"
    else:
        body += "\nMeet at the location above. Bring exact cash or Venmo/Zelle.\n"
    return {"to": buyer_email, "subject": subject, "body": body}
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest backend/tests/test_email_notify.py -v`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add backend/email_notify.py backend/tests/test_email_notify.py
git commit -m "feat: add email notification composition module"
```

---

## Chunk 3: Frontend Updates

### Task 10: Dashboard — Add Donate/Store Tabs + Pickup Type

**Files:**
- Modify: `frontend/src/components/Dashboard.jsx`
- Modify: `frontend/src/components/ListingCard.jsx`

- [ ] **Step 1: Expand tabs in Dashboard.jsx**

In `frontend/src/components/Dashboard.jsx`, replace lines 4-5:

```javascript
const TABS = ["draft", "active", "sold", "donate", "store"];
const TAB_LABELS = {
  draft: "Drafts",
  active: "Active",
  sold: "Sold",
  donate: "Donate",
  store: "Store",
};
```

Update the empty state messages (the ternary block around lines 179-195) to handle the new tabs:

```javascript
const EMPTY_MESSAGES = {
  draft: { icon: "&#128221;", title: "No drafts yet", sub: "Use Gemini to scan your photos and create listings" },
  active: { icon: "&#128722;", title: "No active listings", sub: "Approve some drafts to start selling" },
  sold: { icon: "&#127881;", title: "No sold items yet", sub: "Sold items will appear here" },
  donate: { icon: "&#127873;", title: "No items for donation", sub: "Items past deadline without action go here" },
  store: { icon: "&#128230;", title: "No stored items", sub: "High-value keepers go here" },
};
```

Replace the existing empty state JSX with:

```jsx
const msg = EMPTY_MESSAGES[activeTab] || EMPTY_MESSAGES.draft;
// then use msg.icon, msg.title, msg.sub in the render
```

- [ ] **Step 2: Add batch donate/store buttons for active tab**

In the toolbar section of `Dashboard.jsx`, add after the "Approve Selected" button (only visible on the active tab):

```jsx
{activeTab === "active" && selected.size > 0 && (
  <>
    <button className="btn btn-ghost" onClick={() => handleBatchStatus("donate")}>
      Donate ({selected.size})
    </button>
    <button className="btn btn-ghost" onClick={() => handleBatchStatus("store")}>
      Store ({selected.size})
    </button>
  </>
)}
```

Add the handler:

```javascript
const handleBatchStatus = async (newStatus) => {
  if (selected.size === 0) return;
  try {
    const res = await fetch("/api/listings/batch-status", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: [...selected], status: newStatus }),
    });
    if (res.ok) {
      setSelected(new Set());
      fetchListings();
    }
  } catch {}
};
```

- [ ] **Step 3: Add pickup_type and pricing_strategy display to ListingCard.jsx**

In `ListingCard.jsx`, add after the category/condition section (around line 268):

```jsx
{/* Pickup type + Pricing strategy */}
{(listing.pickup_type || listing.pricing_strategy) && (
  <div style={{
    display: "flex", gap: "var(--space-sm)",
    marginTop: "var(--space-sm)", flexWrap: "wrap",
  }}>
    {listing.pickup_type && (
      <span style={{
        background: listing.pickup_type === "home"
          ? "rgba(245, 166, 35, 0.15)" : "rgba(78, 205, 196, 0.15)",
        color: listing.pickup_type === "home"
          ? "var(--accent-amber)" : "var(--accent-teal)",
        padding: "4px 12px", borderRadius: "100px", fontSize: "15px",
      }}>
        {listing.pickup_type === "home" ? "Home Pickup" : "Meeting Spot"}
      </span>
    )}
    {listing.pricing_strategy && listing.pricing_strategy !== "aggressive" && (
      <span style={{
        background: "rgba(233, 69, 96, 0.15)",
        color: "var(--accent-coral)",
        padding: "4px 12px", borderRadius: "100px", fontSize: "15px",
      }}>
        {listing.pricing_strategy === "hold" ? "Price Hold" : "Fire Sale"}
      </span>
    )}
  </div>
)}
```

- [ ] **Step 4: Test manually**

Run: `cd frontend && npx vite --port 5173` (in one terminal)
Run: `cd snap-and-sell && python3 -m uvicorn backend.api:app --port 5001 --reload` (in another)

Verify:
- Dashboard shows 5 tabs
- Active listings can be batch-moved to donate/store
- Donate/store tabs show the right listings

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Dashboard.jsx frontend/src/components/ListingCard.jsx
git commit -m "feat: add donate/store tabs, batch status actions, pickup/strategy badges"
```

---

### Task 11: Marketplace — Show Current Price + Urgency

**Files:**
- Modify: `frontend/src/components/MarketplaceCard.jsx`

- [ ] **Step 1: Read MarketplaceCard.jsx**

Read the file to understand current structure before modifying.

- [ ] **Step 2: Add current_price display with original strikethrough**

In `MarketplaceCard.jsx`, in the price display section, replace the current price rendering with:

```jsx
{/* Price display */}
<div style={{ display: "flex", alignItems: "baseline", gap: "var(--space-sm)" }}>
  <div className="price">
    ${listing.current_price != null
      ? Number(listing.current_price).toFixed(2)
      : listing.asking_price != null
      ? Number(listing.asking_price).toFixed(2)
      : "---"}
  </div>
  {listing.current_price != null &&
    listing.asking_price != null &&
    listing.current_price < listing.asking_price && (
    <span style={{
      textDecoration: "line-through",
      color: "var(--text-muted)",
      fontSize: "var(--text-sm)",
    }}>
      ${Number(listing.asking_price).toFixed(2)}
    </span>
  )}
</div>
```

Add urgency indicator:

```jsx
{listing.days_remaining != null && listing.days_remaining <= 5 && (
  <div style={{
    marginTop: "var(--space-sm)",
    padding: "4px 12px",
    background: listing.days_remaining <= 2
      ? "rgba(233, 69, 96, 0.2)" : "rgba(245, 166, 35, 0.15)",
    color: listing.days_remaining <= 2
      ? "var(--accent-coral)" : "var(--accent-amber)",
    borderRadius: "100px",
    fontSize: "15px",
    fontWeight: 700,
    display: "inline-block",
  }}>
    {listing.days_remaining === 0
      ? "Last day!"
      : `${listing.days_remaining} day${listing.days_remaining !== 1 ? "s" : ""} left`}
  </div>
)}
```

- [ ] **Step 3: Test manually**

With both servers running, visit the marketplace. Create a listing with a deadline 5 days out and verify:
- Current price shows the discounted amount
- Original price has strikethrough
- Urgency badge appears

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/MarketplaceCard.jsx
git commit -m "feat: show countdown price with strikethrough original and urgency badges"
```

---

## Chunk 4: Deployment + Cross-Posting

### Task 12: Production Build Configuration

**Files:**
- Modify: `backend/api.py` (serve static files in production)
- Create: `Dockerfile`
- Create: `render.yaml`

- [ ] **Step 1: Add static file serving to api.py**

At the end of `backend/api.py`, add static file serving for production:

```python
# --- Static file serving (production) ---
# This must be LAST so it doesn't shadow API routes

frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
if os.path.isdir(frontend_dist):
    from starlette.responses import FileResponse

    # Serve static assets
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="frontend-assets")

    @app.get("/{path:path}")
    def spa_fallback(path: str):
        """SPA fallback — serve index.html for all non-API routes."""
        index = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Not found")
```

- [ ] **Step 2: Create Dockerfile**

Create `Dockerfile` in project root:

```dockerfile
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist
RUN mkdir -p data photos

EXPOSE 5001
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "5001"]
```

- [ ] **Step 3: Create render.yaml**

Create `render.yaml` in project root:

```yaml
services:
  - type: web
    name: snap-and-sell
    runtime: docker
    plan: free
    envVars:
      - key: BASE_URL
        value: https://snap-and-sell.onrender.com
      - key: REBRANDLY_API_KEY
        sync: false
      - key: NOTIFICATION_EMAIL
        value: karthik@balasubramanian.us
      - key: GOOGLE_VOICE_NUMBER
        value: "+1-202-684-6252"
      - key: HOME_ADDRESS
        sync: false
    disk:
      name: snap-sell-data
      mountPath: /app/data
      sizeGB: 1
```

- [ ] **Step 4: Test the build locally**

```bash
cd frontend && npm run build && cd ..
BASE_URL=http://localhost:5001 python3 -m uvicorn backend.api:app --port 5001
```

Visit `http://localhost:5001` — should serve the React app. Visit `http://localhost:5001/api/health` — should return `{"status": "ok"}`.

- [ ] **Step 5: Commit**

```bash
git add backend/api.py Dockerfile render.yaml
git commit -m "feat: add production build config with Dockerfile and Render deployment"
```

---

### Task 13: Deploy to Render

- [ ] **Step 1: Push to GitHub**

```bash
git push origin main
```

- [ ] **Step 2: Create Render service**

Go to Render dashboard → New → Web Service → Connect `kartbala/snap-and-sell` repo. Render should detect the `render.yaml` and auto-configure. Set the secret env vars (`REBRANDLY_API_KEY`, `HOME_ADDRESS`) manually in the Render dashboard.

- [ ] **Step 3: Verify deployment**

Once deployed, visit the Render URL. Verify:
- Marketplace loads
- Dashboard loads
- API health check returns OK

- [ ] **Step 4: Configure custom domain (optional)**

Point a subdomain (e.g., `sell.karthik.link`) to the Render service via CNAME.

- [ ] **Step 5: Update BASE_URL**

Update the `BASE_URL` env var in Render to the final domain.

- [ ] **Step 6: Commit any follow-up fixes**

---

### Task 14: Cross-Posting Workflow Documentation

The cross-posting engine is a **Claude Code session workflow**, not backend code. Document the workflow so it can be triggered by asking Claude.

**Files:**
- Create: `docs/cross-posting-workflow.md`

- [ ] **Step 1: Write the workflow doc**

Create `docs/cross-posting-workflow.md`:

```markdown
# Cross-Posting Workflow

## Prerequisites
- Karthik is logged in to Craigslist and Facebook Marketplace in Chrome
- Claude-in-Chrome extension is active

## Post New Listings
1. GET /api/listings?status=active to get all active listings
2. For each listing without external posts:
   a. Open Craigslist DC > "for sale by owner"
   b. Fill in: title, description, asking_price (use current_price), category, photos
   c. Post and capture the URL
   d. POST external post record: platform=craigslist, url=<captured>
   e. Open Facebook Marketplace > Create listing
   f. Fill in same details
   g. Capture URL, record external post

## Update Stale Prices
1. GET /api/external-posts/stale
2. For each stale post:
   a. Navigate to the URL
   b. Edit the price to match current_price
   c. Update status to 'active'

## Remove Sold/Donated/Stored
1. GET /api/listings?status=sold (and donate, store)
2. For each with external posts:
   a. Navigate to post URL
   b. Delete/remove the listing
   c. Update post status to 'removed'
```

- [ ] **Step 2: Commit**

```bash
git add docs/cross-posting-workflow.md
git commit -m "docs: add cross-posting workflow for Claude-in-Chrome sessions"
```

---

## Dependency Graph

```
Task 1 (schema) ──→ Task 2 (models) ──→ Task 3 (pricing) ──→ Task 4 (marketplace API)
                                                              ↓
                                                         Task 5 (offers API)
                                                              ↓
Task 1 ──→ Task 7 (end-of-life) ──→ Task 10 (frontend dashboard)
Task 1 ──→ Task 8 (external posts) ──→ Task 14 (cross-posting doc)
Task 3 ──→ Task 9 (email notify)
Task 6 (share.py BASE_URL) — independent
Task 4 + Task 10 ──→ Task 11 (marketplace frontend)
Task 12 (deployment config) ──→ Task 13 (deploy to Render)
```

**Independent tasks that can be parallelized:**
- Task 6 (share.py) — no dependencies
- Task 8 (external posts) — only depends on Task 1
- Task 9 (email notify) — only depends on Task 3
- Task 14 (cross-posting doc) — only needs Task 8 done

---

## Deferred Items (Not in This Plan)

These spec items are intentionally deferred to keep the plan focused. They can be added as follow-up tasks:

1. **Daily email digest nudges** (spec Section 5) — "X items expiring soon" emails at 7-day and 3-day marks. Requires a trigger mechanism (cron, Claude Code session, or manual).
2. **Printable donate/store lists** (spec Section 5) — batch report with item names and original prices for tax receipts. Simple endpoint, can be added anytime.
3. **Auto-tagging pickup_type during intake** (spec Section 7) — auto-set `home` for furniture/appliances. Currently manual via dashboard. Can be added to `intake.py` later.
4. **Automatic stale price detection** — utility function to compare `last_price_posted` against `compute_current_price()` and flag mismatches. Currently manual via Claude Code sessions.
5. **`asking_price` vs `original_price` naming clarification** — the marketplace returns `asking_price` (undiscounted) alongside `current_price` (discounted). The existing `original_price` column is purchase/retail price, not asking price. No aliasing needed — context makes the distinction clear.
