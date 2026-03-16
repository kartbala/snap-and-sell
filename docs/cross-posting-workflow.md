# Cross-Posting Workflow

Claude-in-Chrome workflow for posting listings to Craigslist and Facebook Marketplace.

## Prerequisites
- Karthik is logged in to Craigslist and Facebook Marketplace in Chrome
- Claude-in-Chrome extension is active
- Snap & Sell backend is running (local or deployed)

## Post New Listings

1. `GET /api/listings?status=active` to get all active listings
2. For each listing without external posts:
   a. **Craigslist:**
      - Open Craigslist DC > "for sale by owner"
      - Fill in: title, description, current_price (from marketplace API), category, photos
      - Post and capture the resulting URL
      - Record via API: `POST /api/listings/{lid}/external-posts` with `platform=craigslist, url=<captured>`
   b. **Facebook Marketplace:**
      - Open Facebook Marketplace > Create new listing
      - Fill in same details (title, description, current_price, category, photos)
      - Capture URL after posting
      - Record via API: `POST /api/listings/{lid}/external-posts` with `platform=facebook, url=<captured>`

## Update Stale Prices

When countdown pricing changes the current_price, external posts become stale.

1. `GET /api/external-posts/stale` to find posts needing price updates
2. For each stale post:
   a. Navigate to the post URL
   b. Edit the price to match the listing's current `current_price` (from `GET /api/marketplace`)
   c. Update the post status: `PUT /api/external-posts/{pid}` with `status=active`

## Remove Sold/Donated/Stored Listings

When listings leave the active state, their external posts should be removed.

1. `GET /api/listings?status=sold` (repeat for `donate` and `store`)
2. For each listing that has external posts:
   a. Navigate to the external post URL
   b. Delete/remove the listing from the platform
   c. Update post status: `PUT /api/external-posts/{pid}` with `status=removed`

## Triggering This Workflow

Ask Claude: "Cross-post my active listings" or "Update stale prices on Craigslist/Facebook" during a Claude Code session with Chrome automation active.
