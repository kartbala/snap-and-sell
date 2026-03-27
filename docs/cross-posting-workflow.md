# Cross-Posting Workflow

## Automated (Recommended)

Use the `cross_poster` CLI tool to post listings to Craigslist and Facebook Marketplace with photos.

### First-Time Setup

```bash
# Install dependencies
pip install playwright requests
playwright install chromium

# Log in to each platform (one-time, saved to browser profile)
python -m cross_poster setup --platform craigslist
python -m cross_poster setup --platform facebook
```

### Posting

```bash
# List what will be posted
python -m cross_poster list

# Post all items to both platforms
python -m cross_poster post

# Post to one platform
python -m cross_poster post --platform craigslist

# Post one item
python -m cross_poster post --item "Schwinn"

# Dry run (preview without publishing)
python -m cross_poster post --dry-run
```

### Data Sources

1. **Snap & Sell API** (primary): pulls active listings from `GET /api/marketplace`
2. **listings.json** (fallback): edit `cross_poster/listings.json` directly

### After Posting

Successful posts are recorded to the Snap & Sell API via `POST /api/listings/{id}/external-posts`. If the API is unavailable, results are saved to `cross_poster/results.json`.

## Manual (Claude-in-Chrome)

For one-off posts or when the CLI isn't available, ask Claude:
"Cross-post my active listings" or "Post [item] to Craigslist"
during a Claude Code session with Chrome automation active.

## Price Updates & Removal

Not yet automated. Use the Snap & Sell dashboard or edit listings manually on each platform.
