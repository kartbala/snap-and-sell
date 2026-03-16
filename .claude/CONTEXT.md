# Snap & Sell — Project Context

## What It Is
Zero-cost personal MVP for selling items locally. Photo intake via Gemini web, batch review UI, public marketplace, rule-based negotiation.

## Repo
https://github.com/kartbala/snap-and-sell

## Tech Stack
- **Backend:** Python 3.11 + FastAPI (port 5001), SQLite, Pydantic
- **Frontend:** React 19 + Vite 6 (port 5173), react-router-dom
- **Fonts:** Atkinson Hyperlegible (low vision), Fraunces (display)
- **Theme:** Dark (#1a1a2e bg, #fff text, #e94560 coral, #4ecdc4 teal, #f5a623 amber)
- **Accessibility:** 22px base font, 48px touch targets, 3px focus rings

## Project Structure
```
snap-and-sell/
├── backend/
│   ├── database.py      # SQLite schema (listings, photos, offers, notifications)
│   ├── models.py        # Pydantic models + CRUD (inc. notifications)
│   ├── api.py           # FastAPI (18 endpoints, port 5001)
│   ├── negotiation.py   # Rule-based offer engine
│   ├── intake.py        # Gemini text parser + price heuristics
│   ├── meeting_spots.py # 15 DC safe exchange locations
│   ├── share.py         # Rebrandly short link generation
│   └── tests/           # 276 tests across 18 files
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx       # Seller: tabs, inline edit, batch approve
│   │   │   ├── ListingCard.jsx     # Seller card with inline editing
│   │   │   ├── Marketplace.jsx     # Public browse + offer modal trigger
│   │   │   ├── MarketplaceCard.jsx # Public card
│   │   │   └── OfferModal.jsx      # Offer form + instant result display
│   │   ├── App.jsx          # Router (/ = marketplace, /dashboard = seller)
│   │   ├── main.jsx
│   │   └── index.css        # Full design system with CSS variables
│   └── vite.config.js       # Proxy /api and /photos to :5001
├── photos/              # Item photos (served statically)
├── data/                # SQLite DB (gitignored)
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
| GET | /api/marketplace | Active only, NO min_price, excludes >30 days, includes days_remaining |
| POST | /api/offers | Submit offer (auto-negotiation, accepted includes meeting_spot) |
| GET | /api/listings/{id}/offers | Offers for listing |
| GET | /api/meeting-spots | All 15 DC safe exchange locations |
| GET | /api/notifications?sent= | List notifications (filter by sent) |
| GET | /api/notifications/count | Unsent notification count |
| PUT | /api/notifications/{id} | Mark notification as sent |
| POST | /api/listings/{id}/share | Generate Rebrandly short link |

## Negotiation Rules
- offer >= asking_price → accepted
- offer >= min_price → accepted
- offer < min_price → rejected (message shows asking price)
- offer <= 0 → rejected (invalid)
- min_price is None, offer < asking → pending (manual review)

## Intake Parser
Parses Gemini numbered bold-item format. Depreciation: electronics 55%, furniture 35%, fitness 40%, audio 50%. Min price = 70% of asking.

## Test Coverage: 276 tests
- test_database.py (10), test_models.py (17), test_models_edge_cases.py (27)
- test_api.py (15), test_api_edge_cases.py (28), test_api_lifecycle.py (19)
- test_negotiation.py (13), test_negotiation_edge_cases.py (33)
- test_intake.py (14), test_intake_edge_cases.py (22)
- test_integration.py (3), test_e2e_scenarios.py (19)
- test_meeting_spots.py (17), test_expiration.py (14)
- test_schema_migration.py (7), test_notifications.py (10)
- test_notifications_api.py (9), test_price_comps.py (7), test_share.py (12)

## Bugs Found & Fixed
1. negotiation.py: TypeError crash when asking_price=None with min_price set (fixed)
2. Vite 7 incompatible with Node 21.6.2 — pinned to Vite 6

## Known Issues
1. `test_update_sets_updated_at` — pre-existing flaky test. SQLite `datetime('now')` returns UTC (`2026-03-08 01:05:24`) but Python `datetime.now().isoformat()` returns local time (`2026-03-07T20:05:24`). String comparison fails across the format boundary. Not a real bug — cosmetic test issue.

## Gemini Intake Workflow (Claude Code session, not scripted)
1. Navigate to gemini.google.com via Claude-in-Chrome
2. Prompt: "@Google Photos last N photos. Identify brand/model. Search @Gmail for receipts."
3. Wait 30-60s, read with get_page_text
4. Parse with intake.parse_gemini_response()
5. For each: download photo, Perplexity price comps, POST /api/listings
6. Report draft count

## Implemented Improvements
1. **Meeting spot suggestion** — 15 curated DC safe exchange locations (police stations, libraries, metro stations, public places). Accepted offers automatically include a suggested meeting spot.
2. **Listing expiration** — marketplace auto-hides listings >30 days old. Each marketplace listing includes `days_remaining`. Urgency styling when <=5 days left. Sellers still see expired items in dashboard.
3. **Offer notifications** — new offers auto-create notifications. Dashboard shows unsent count badge. API supports list/filter/mark-sent. Enriched with listing title, buyer name, offer amount, decision.
4. **Price comparison display** — `price_comps` JSON column on listings. Dashboard shows full breakdown (source, price, note). Marketplace shows range summary ("Similar: $425–$500"). Stored during intake.
5. **Share links** — Rebrandly short links on `karthik.link` domain. One-click generate from active listing cards. Idempotent (returns existing link on re-click). Copies to clipboard. `REBRANDLY_API_KEY` required in `.env`.

## Remaining Improvements (from competitive research)
1. **SMS notifications via Google Voice** — text Karthik on new offers, text buyer on accept with pickup details
2. **Chat/messaging** — in-app or SMS-based buyer-seller communication

## Key Competitive Insight
Strongest differentiator: AI-powered intake (no competitor auto-scans photos + finds receipts + auto-prices). Instant negotiation also unique — removes tedious back-and-forth.

## Deployment
- **Render.com:** Previously attempted, did not work (possible user error — needs investigation)
- **Alternatives to consider:** GitHub Pages (static) + Railway/Fly.io (backend), or Cloudflare Pages + Workers

## Running
```bash
# Backend
cd snap-and-sell && python3 -m uvicorn backend.api:app --port 5001 --reload
# Frontend
cd frontend && npx vite --port 5173
# Tests
python3 -m pytest backend/tests/ -v
```

## Related Context
- `~/.claude/reference/mcp-servers.md` — Perplexity, Google Voice, Rebrandly configs
- `~/.claude/reference/gemini-web-best-practices.md` — Gemini intake patterns
- `org-roam/communication.org` — Google Voice setup for buyer SMS
