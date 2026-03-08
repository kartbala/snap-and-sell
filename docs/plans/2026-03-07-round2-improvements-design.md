# Snap & Sell — Round 2 Improvements Design

**Date:** 2026-03-07
**Status:** Approved

## Features

### 1. Email Notifications

New offer comes in → store notification record → Claude Code session polls pending notifications → sends email to kartbala@gmail.com via Google Workspace MCP.

**Schema:** New `notifications` table:
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `listing_id INTEGER NOT NULL` (FK → listings)
- `offer_id INTEGER NOT NULL` (FK → offers)
- `type TEXT NOT NULL` ("new_offer")
- `sent INTEGER NOT NULL DEFAULT 0`
- `created_at TEXT NOT NULL DEFAULT (datetime('now'))`

**Endpoints:**
- `GET /api/notifications?sent=false` — list pending notifications (joined with listing + offer data)
- `PUT /api/notifications/{id}` — mark as sent

**Email content:** Item title, offer amount, buyer name/phone, decision, meeting spot if accepted.

**Frontend:** Notification badge on Dashboard showing unsent count.

**Not automated:** Email sending requires active Claude Code session with Google Workspace MCP.

### 2. Price Comparisons

During Gemini intake (Claude Code session), after parsing items and before creating drafts, search Perplexity for comparable prices. Store results on the listing.

**Schema:** Add `price_comps TEXT` column to listings table (JSON string).

**JSON format:** Array of `{"source": "eBay", "price": 450.0, "url": "...", "note": "sold listing"}`

**Model changes:** Add `price_comps` field (str | None) to ListingCreate, ListingUpdate, ListingResponse.

**Frontend:**
- Dashboard: show comps on draft cards to help pricing decisions.
- MarketplaceCard: show comps to build buyer confidence ("Similar items sell for $X–$Y").

**Not automated:** Perplexity search happens during Claude Code intake sessions only.

### 3. Share Links

Seller clicks "Share" on an active listing → backend calls Rebrandly REST API → stores short URL → copies to clipboard.

**Schema:** Add `share_url TEXT` column to listings table.

**Endpoint:** `POST /api/listings/{id}/share`
- Calls Rebrandly REST API directly (API key in .env)
- Domain: `karthik.link`
- Slashtag: auto-generated from listing title
- Stores result in `share_url` column
- Returns `{"share_url": "https://karthik.link/samsung-tv"}`

**Model changes:** Add `share_url` field (str | None) to ListingResponse.

**Frontend:**
- Dashboard: "Share" button on active listings. Copies URL to clipboard, shows confirmation.
- MarketplaceCard: if share_url exists, could display it (optional).

**Fully automated:** No Claude Code session needed — direct API call.

## Decisions

- Email over SMS (Google Voice is reply-only; Twilio deferred)
- Price comps at intake time only (not on-demand refresh)
- `karthik.link` domain via personal Rebrandly account
- Direct Rebrandly REST API (not MCP workflow)
- Chat/messaging deferred entirely

## Schema Migration

SQLite ALTER TABLE for two new columns + one new table:
```sql
ALTER TABLE listings ADD COLUMN price_comps TEXT;
ALTER TABLE listings ADD COLUMN share_url TEXT;

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
