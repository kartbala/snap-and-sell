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

### New fields on listings

- `deadline` — date, defaults to 2026-06-01, overridable per item
- `pricing_strategy` — enum: `hold`, `aggressive` (default), `fire_sale`
- `current_price` — computed field, never stored. Derived from `asking_price` + strategy + days remaining.

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

- `asking_price` is immutable (original price preserved)
- Marketplace API returns `current_price` computed at query time
- Negotiation engine uses `current_price` as the new reference point
- `min_price` still respected — drops never go below it

## 3. Cross-Posting Engine

### Workflow

1. Karthik batch-approves listings in dashboard
2. Triggers "Cross-Post" action from dashboard (not automatic)
3. Claude-in-Chrome session opens Craigslist/FB Marketplace in logged-in browser
4. Fills in: title, description, price, photos, category, location (Washington DC)
5. External listing ID/URL stored on the listing record

### Data model

New `external_posts` JSON column on listings:
```json
[
  {"platform": "craigslist", "url": "https://...", "posted_at": "2026-04-01", "status": "active"},
  {"platform": "facebook", "url": "https://...", "posted_at": "2026-04-01", "status": "active"}
]
```

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

Add optional fields to the offer form:
- `buyer_email` (optional but encouraged)
- `buyer_phone` (optional, for future SMS)

## 5. End-of-Life Manager

### Terminal states (replace `expired`)

- **`donate`** — goes to Goodwill, Habitat ReStore, etc.
- **`store`** — high-value, low-volume keeper

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

- **Single service:** FastAPI backend serves the API + static React build
- **SQLite on persistent disk** — fine for single-seller, single-instance
- **Photos:** Served from the deployment (small files, 50-150 items)

### Domain

Point a subdomain (e.g., on `karthik.link` or `balasubramanian.org`) to the deployment.

### Environment variables

- `REBRANDLY_API_KEY` (exists)
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
