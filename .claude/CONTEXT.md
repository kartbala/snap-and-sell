# Snap & Sell — Project Context

## What It Is
Zero-cost personal MVP for selling items locally in DC. Photo intake via Gemini web, batch review UI, public marketplace, rule-based negotiation, countdown pricing, and cross-posting workflow.

## Repo
https://github.com/kartbala/snap-and-sell

## Deployment
- **Live at:** https://snap-and-sell.onrender.com
- **Render service:** snap-and-sell (Docker, Starter plan, auto-deploy from main)
- **Service ID:** srv-d6s2fria214c73bpfa90
- **Persistent disk:** 1GB at `/app/data` (mount name `snap-sell-data`) — SQLite DB + uploaded photos survive deploys. No re-seeding needed.
- **Env vars set:** BASE_URL, NOTIFICATION_EMAIL, GOOGLE_VOICE_NUMBER, HOME_ADDRESS
- **Env vars synced separately (sync: false in render.yaml):** REBRANDLY_API_KEY, HOME_ADDRESS — set in Render dashboard, not version-controlled.
- **Static file serving fix:** The SPA fallback `/{path:path}` must check for real files in `frontend/dist` before returning `index.html`, otherwise JS/CSS get served as HTML and React fails to mount.

## Tech Stack
- **Backend:** Python 3.11 + FastAPI (port 5001), SQLite, Pydantic
- **Frontend:** React 19 + Vite 6 (port 5173), react-router-dom
- **Fonts:** Atkinson Hyperlegible (low vision), Fraunces (display)
- **Theme:** Dark (#1a1a2e bg, #fff text, #e94560 coral, #4ecdc4 teal, #f5a623 amber)
- **Accessibility:** 22px base font, 48px touch targets, 3px focus rings
- **Deployment:** Render.com (Docker), GitHub auto-deploy

## Project Structure
```
snap-and-sell/
├── backend/
│   ├── database.py      # SQLite schema (listings, photos, offers, notifications, external_posts)
│   ├── models.py        # Pydantic models + CRUD (inc. notifications)
│   ├── api.py           # FastAPI (22+ endpoints, port 5001, static file serving)
│   ├── negotiation.py   # Rule-based offer engine
│   ├── intake.py        # Gemini text parser + price heuristics
│   ├── meeting_spots.py # 15 DC safe exchange locations
│   ├── share.py         # Rebrandly short link generation (uses BASE_URL env var)
│   ├── pricing.py       # Countdown price computation (aggressive/fire_sale/hold)
│   ├── external_posts.py # External cross-posting CRUD (Craigslist/FB)
│   ├── email_notify.py  # Email notification composition
│   └── tests/           # 308 tests across 20+ files
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx       # 5 tabs (draft/active/sold/donate/store), batch actions
│   │   │   ├── ListingCard.jsx     # Pickup type + pricing strategy badges
│   │   │   ├── Marketplace.jsx     # Public browse + offer modal
│   │   │   ├── MarketplaceCard.jsx # Current price, strikethrough original, urgency badges
│   │   │   └── OfferModal.jsx      # Offer form + instant result display
│   │   ├── App.jsx          # Router (/ = marketplace, /dashboard = seller)
│   │   ├── main.jsx
│   │   └── index.css        # Full design system with CSS variables
│   └── vite.config.js       # Proxy /api and /photos to :5001
├── photos/              # Item photos (served statically)
├── data/                # SQLite DB (gitignored)
├── Dockerfile           # Multi-stage: node:20-slim (frontend build) + python:3.11-slim
├── render.yaml          # Render service config
├── docs/
│   └── cross-posting-workflow.md  # Claude-in-Chrome workflow for Craigslist/FB
└── requirements.txt     # fastapi, uvicorn, pydantic, python-multipart, pytest, httpx
```

## API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/health | Health check |
| POST | /api/listings | Create draft |
| GET | /api/listings?status= | List (seller) |
| GET | /api/listings/{id} | Get one |
| PUT | /api/listings/{id} | Update |
| DELETE | /api/listings/{id} | Delete |
| POST | /api/listings/batch-approve | Approve drafts -> active |
| POST | /api/listings/batch-status | Batch status change (donate/store) |
| GET | /api/marketplace | Active, deadline-filtered, includes current_price + photos |
| POST | /api/offers | Submit offer (uses current_price for negotiation) |
| GET | /api/listings/{id}/offers | Offers for listing |
| POST | /api/listings/{id}/photos | Upload photo (multipart) |
| GET | /api/listings/{id}/photos | List photos for listing |
| GET | /api/meeting-spots | All 15 DC safe exchange locations |
| GET | /api/notifications?sent= | List notifications |
| GET | /api/notifications/count | Unsent count |
| PUT | /api/notifications/{id} | Mark sent |
| POST | /api/listings/{id}/share | Generate Rebrandly short link |
| GET | /api/listings/{id}/external-posts | List cross-posts |
| POST | /api/listings/{id}/external-posts | Record a new cross-post (CL/FB) |
| GET | /api/external-posts/stale | Stale cross-posts needing price update |
| PUT | /api/external-posts/{id}/status | Flip cross-post status (active/price_stale/removed) |

## Liquidation Command Center (Chunks 1-4 Complete)
New columns on listings: `deadline`, `pricing_strategy`, `pickup_type`. New table: `external_posts`.

### Pricing Strategies
- **aggressive** (default): Linear discount from asking to min_price as deadline approaches
- **fire_sale**: Steeper discounts, items you want gone fast
- **hold**: No discount, stays at asking_price until deadline

### Listing Lifecycle
draft → active → sold/donate/store. Marketplace only shows active + before deadline.

### Photo Upload
POST multipart file to `/api/listings/{id}/photos`. First photo auto-set as primary. Photos served from `/photos/` directory. Marketplace response includes `photos` array.

## Current Listings
DB is the source of truth — query `GET /api/listings` for live state. Persistent disk means listings + photos survive deploys; no seeding script needed.

```bash
# Quick status snapshot
curl -s https://snap-and-sell.onrender.com/api/listings | \
  python3 -c "import sys,json; d=json.load(sys.stdin); \
  print(f'{len(d)} total | {sum(1 for x in d if x[\"status\"]==\"active\")} active | {sum(1 for x in d if x[\"status\"]==\"sold\")} sold')"
```

## Purchase History Sources
- **IKEA:** Full order history at `Sandbox/netherlands-move/ikea-purchase-history.md` (79 orders, $9,599 total)
- **Amazon:** Search via Chrome browser at `amazon.com/your-orders/search?search=TERM` (see `~/.claude/reference/amazon-order-lookup.md`)
- **Walmart:** Search Gmail `from:walmart.com` for order confirmations
- **Photos:** Google Photos search (AI labels + OCR). Photos of items taken from iPhone 16 Pro Max.

## Negotiation Rules
- offer >= asking_price → accepted
- offer >= min_price → accepted
- offer < min_price → rejected (message shows current price, not asking)
- offer <= 0 → rejected (invalid)
- min_price is None, offer < asking → pending (manual review)

## Intake Parser
Parses Gemini numbered bold-item format. Depreciation: electronics 55%, furniture 35%, fitness 40%, audio 50%. Min price = 70% of asking.

## Test Coverage: 308 tests
- test_database.py, test_models.py, test_models_edge_cases.py
- test_api.py, test_api_edge_cases.py, test_api_lifecycle.py
- test_negotiation_edge_cases.py
- test_intake.py, test_intake_edge_cases.py
- test_integration.py, test_e2e_scenarios.py
- test_meeting_spots.py, test_expiration.py
- test_schema_migration.py, test_notifications.py
- test_notifications_api.py, test_price_comps.py, test_share.py
- test_pricing.py (17), test_end_of_life.py (8), test_external_posts.py (8), test_email_notify.py (4)

## Known Issues
1. **REBRANDLY_API_KEY** — set as `sync: false` in render.yaml; must be configured in Render dashboard. Share links won't generate without it. Local dev: source from `~/.env~` or 1Password.
2. **AOC monitor return email** — Walmart shows a return initiated April 2019 for the AOC C4008VU8, but Karthik confirmed he still owns it. Return may not have been completed.
3. **FRIHETEN listing photo** — Currently using IKEA price tag photo. Needs actual photo of the couch in home.
4. **CL deletion not automated** — `cross_poster/` only handles posting. To mark a CL post sold, delete via accounts.craigslist.org (Chrome MCP), then `PUT /api/external-posts/{id}/status` with `{"status":"removed"}`.

## Running
```bash
# Backend
cd snap-and-sell && python3 -m uvicorn backend.api:app --port 5001 --reload
# Frontend
cd frontend && npx vite --port 5173
# Tests
python3 -m pytest backend/tests/ -v
# Production build (local test)
cd frontend && npm run build && cd .. && BASE_URL=http://localhost:5001 python3 -m uvicorn backend.api:app --port 5001
```

## Image Analysis for Listings (Tested 2026-03-26)

**Recommended: Gemini 2.5 Flash API** — best at reading brand names, model numbers, weight markings, warning labels, and fine text on equipment. Use for auto-populating listing titles, descriptions, and specs from photos.

### Approach Comparison (tested on 30 gym equipment photos)
| Approach | Speed | OCR Quality | Cost | Production-Ready? |
|----------|-------|-------------|------|-------------------|
| **Gemini 2.5 Flash API** | ~20s/image | Excellent (reads brands, models, serial #s) | Free (250 req/day) | Yes |
| **Claude Vision** | ~4s (parallel) | Good but hedges on brands | Included | Yes, for speed |
| **Gemini CLI** | ~5 min/image | Excellent (same model) | Free but rate-limited hard | No (too slow) |
| **Gemini Web App** | Manual upload | Can't access Google Photos directly | $20/mo plan | No (not automatable) |

### Implementation
- **Script:** `Sandbox/potomac-gym-inventory/analyze-gym-api.py` — working batch processor
- **SDK:** `google-genai` (pip), uses `types.Part.from_bytes()` for image input
- **API Key:** In `~/.env~` as `GEMINI_API_KEY` (kartbala@gmail.com, free tier, project: gen-lang-client-0583310430)
- **Structured output:** Use `response_mime_type="application/json"` + Pydantic schema for consistent extraction
- **Rate limiting:** 10 RPM on Flash free tier; add 7s delay between calls; large images (~4MB) consume more tokens

### Key Finding
Gemini identified "Paramount MP Series" brand/model from a gym machine photo where Claude guessed "possibly Inspire Fitness." Gemini read all 16 weight stack increments (20-170 lbs), warning label text, and spotted accessories on the floor. For Snap & Sell's auto-listing feature, this precision matters.

## Related Context
- `~/.claude/reference/mcp-servers.md` — Perplexity, Google Voice, Rebrandly configs
- `~/.claude/reference/amazon-order-lookup.md` — Amazon order search via Chrome
- `~/.claude/reference/ikea-order-lookup.md` — IKEA purchase history lookup
- `Sandbox/netherlands-move/ikea-purchase-history.md` — Full IKEA order extract (79 orders)
- `Sandbox/potomac-gym-inventory/` — Gym photo analysis scripts and results
- `docs/cross-posting-workflow.md` — Claude-in-Chrome workflow for Craigslist/FB
- `org-roam/communication.org` — Google Voice setup for buyer SMS
