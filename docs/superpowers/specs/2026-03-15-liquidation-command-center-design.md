# Snap & Sell: Liquidation Command Center

**Date:** 2026-03-15
**Goal:** Convert Snap & Sell from a local MVP into a deployed, end-to-end household liquidation tool for Karthik & Ashton's move to the Netherlands.
**Hard deadline:** June 1, 2026 (Ashton's mom moves in)
**Estimated items:** 50–150

## 1. System Architecture

Six layers, building on the existing codebase:

1. **Intake** (exists) — Gemini photo sweep for bulk items, manual intake for high-value items. Drafts land in SQLite.
2. **Pricing engine** (exists + new) — Current depreciation heuristics + Perplexity comps + countdown auto-pricing that reduces prices as June 1 approaches.
3. **Marketplace** (exists, needs deployment) — Public React site where buyers browse and submit offers. Deployed on Render (Railway as fallback).
4. **Cross-posting engine** (new) — Claude-in-Chrome automation posts active listings to Craigslist & Facebook Marketplace. Stores external listing IDs for updates/removal.
5. **Notifications** (exists + new) — Email via Google Workspace MCP on new offers (to Karthik) and accepted offers (to buyer).
6. **End-of-life manager** (new) — Countdown price drops, donate/store queues, cross-post cleanup.

Data model stays SQLite. Single seller, personal tool.

## 2. Countdown Auto-Pricing

### Schema changes

New columns on `listings` table (via `ALTER TABLE ADD COLUMN` with defaults, preserving existing data):

- `deadline TEXT DEFAULT '2026-06-01'` — overridable per item
- `pricing_strategy TEXT DEFAULT 'aggressive'` — enum: `hold`, `aggressive`, `fire_sale`
- `pickup_type TEXT DEFAULT 'meeting_spot'` — enum: `home`, `meeting_spot`

**Replaces the existing 30-day rolling expiration model.** The `LISTING_EXPIRY_DAYS` constant and `created_at`-based filtering in `/api/marketplace` are removed. Expiration is now `deadline`-based. The `_days_remaining()` helper changes to `deadline - now()`. Tests in `test_expiration.py` will be rewritten for the deadline model.

`current_price` is computed at query time, never stored. Derived from `asking_price` + strategy + days remaining.

### Drop schedules

**`aggressive` (default):**

| Time remaining | Discount |
|----------------|----------|
| 4+ weeks       | 0%       |
| 3 weeks        | 10%      |
| 2 weeks        | 20%      |
| 1 week         | 35%      |
| Last 3 days    | 50%      |

**`fire_sale`:**
- 5% per day for the last 14 days (cumulative, max 70% off)

**`hold`:**
- No drops. For high-value items Karthik would rather store than discount.

### Behavior

- `asking_price` is not programmatically modified by the countdown engine (original price preserved for reference). Seller can still manually edit it via the dashboard.
- Marketplace API returns `current_price` computed at query time
- Negotiation engine: API layer computes `current_price` and passes it as `asking_price` to `evaluate_offer()`. Rejection messages show the current (discounted) price, not the original. A separate `original_price` field is included in listing responses for display.
- `min_price` still respected — drops never go below it. If `current_price` drops to `min_price`, any offer at or above that amount is auto-accepted.

## 3. Cross-Posting Engine

### Workflow

1. Karthik batch-approves listings in dashboard
2. Triggers "Cross-Post" action from dashboard (not automatic)
3. Claude-in-Chrome session opens Craigslist/FB Marketplace in logged-in browser
4. Fills in: title, description, price, photos, category, location (Washington DC)
5. External listing ID/URL stored on the listing record

### Data model

New `external_posts` table (normalized, consistent with existing `photos`, `offers`, `notifications` tables):

```sql
CREATE TABLE external_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL REFERENCES listings(id),
    platform TEXT NOT NULL,  -- 'craigslist' or 'facebook'
    url TEXT,
    posted_at TEXT DEFAULT (datetime('now')),
    status TEXT DEFAULT 'active',  -- 'active', 'price_stale', 'pending_removal', 'removed'
    last_price_posted REAL
);
```

This makes queries like "find all stale Craigslist posts" straightforward without JSON parsing.

### Platform specifics

- **Craigslist:** DC > "for sale by owner." Track post dates — CL requires renewal every few days. Flag when renewal needed.
- **Facebook Marketplace:** Local selling listing. Track status.

### Price drop sync

When countdown pricing drops a price, external posts flagged as `price_stale`. Batch update via Claude-in-Chrome session.

### Removal

When items sold/donated/stored, external posts flagged for removal. Next Claude-in-Chrome session deletes them.

### Key constraint

Not a background daemon. This is a Claude Code session: "hey Big C, cross-post my new listings" or "update stale prices on Craigslist."

## 4. Notifications (Email Only)

### On new offer (to Karthik)

- **Email to karthik@balasubramanian.us** via Google Workspace MCP
- Contents: item title, offer amount, buyer name, accept/reject/pending decision, link to dashboard

### On accepted offer (to buyer)

- **Email to buyer** (if they provided email in offer form)
- Contents: item title, accepted amount, pickup details (address for home pickup, meeting spot for small items), Karthik's Google Voice number for coordination

### Offer form changes

- `buyer_email` — already exists in schema, models, and React form. No changes needed.
- `buyer_phone` — already exists in schema as a required field (`NOT NULL`). No changes needed.

## 5. End-of-Life Manager

### New terminal statuses

The existing codebase has three statuses: `draft`, `active`, `sold`. There is no `expired` status — expiration is handled at query time. We add two new statuses:

- **`donate`** — goes to Goodwill, Habitat ReStore, etc.
- **`store`** — high-value, low-volume keeper

Dashboard tabs expand from 3 to 5: draft / active / sold / donate / store.

### Dashboard "End of Life" tab

- Shows items within 7 days of deadline
- Each item shows current (dropped) price
- Actions: keep dropping / donate / store
- Items not acted on default to `donate` at deadline

### Outputs

- **Donate list:** Printable batch list with item names and original prices (for tax receipt)
- **Store list:** What's being kept and where

### Automated nudges

Daily email digest when items cross the 7-day and 3-day marks: "X items expiring soon — review in dashboard."

### Cross-post cleanup

Items moved to donate/store flagged for removal from Craigslist/FB.

## 6. Deployment

### Strategy

1. Try Render.com first (already in Karthik's stack, previous attempt had issues — debug)
2. Fallback to Railway.app if Render proves problematic

### Architecture

- **Single service:** FastAPI backend serves the API + static React build. Build step: `cd frontend && npm run build`, then serve `dist/` via FastAPI `StaticFiles` with SPA routing fallback.
- **SQLite on persistent disk** — fine for single-seller, single-instance
- **Photos:** Served from the deployment (small files, 50-150 items)

### Domain

Point a subdomain (e.g., on `karthik.link` or `balasubramanian.org`) to the deployment.

### Environment variables

- `REBRANDLY_API_KEY` (exists)
- `BASE_URL` (new — public URL of deployed site, replaces hardcoded `localhost:5173` in `share.py`)
- `HOME_ADDRESS` (new — only revealed in accepted-offer emails)
- `GOOGLE_VOICE_NUMBER` (new — included in buyer emails)
- `NOTIFICATION_EMAIL` (new — karthik@balasubramanian.us)

## 7. Pickup & Logistics

### Two modes

- **`home`** — large/heavy items (furniture, appliances). Buyer comes to Karthik's address.
- **`meeting_spot`** — small items. Existing 15 DC safe exchange locations.

### Assignment

- Auto-tagged during intake based on category (furniture/appliances → home, everything else → meeting spot)
- Overridable in dashboard

### Privacy

- Home address stored in `.env`, never on public marketplace
- Only revealed in accepted-offer email to the specific buyer
- Meeting spot suggestions continue to work as-is

### Coordination

No scheduling system. Accepted-offer email says "Contact Karthik at [Google Voice] to arrange pickup." Coordination via text/call.

## 8. What's NOT in Scope

- SMS notifications (deferred — email only for now)
- In-app chat/messaging
- Multi-user/multi-seller support
- Payment processing (cash, Venmo, Zelle handled outside the app)
- Mobile app (responsive web is sufficient)
- IKEA buyback integration (separate workflow, already researched)

## 9. Migration & Test Impact

### Schema migration

New columns added via `ALTER TABLE ADD COLUMN` with defaults. Existing data is preserved. No destructive migration needed.

### Test suite impact

- `test_expiration.py` (14 tests) — rewritten for deadline-based model
- Tests that check marketplace filtering — updated for `deadline` instead of `created_at + 30 days`
- New tests needed: countdown pricing computation, end-of-life state transitions, external_posts CRUD, pickup_type assignment, notification email triggers
- Existing negotiation tests remain valid but may need updates for `current_price` pass-through
