from __future__ import annotations
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, date
from functools import lru_cache
import shutil
import uuid
from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from backend.database import init_db, DEFAULT_DB_PATH
from backend import models
from backend.meeting_spots import get_all_spots, suggest_spot, spot_to_dict
from backend.pricing import compute_current_price


@lru_cache
def _get_db_path() -> str:
    return os.environ.get("DB_PATH", DEFAULT_DB_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(_get_db_path())
    yield


app = FastAPI(title="Snap & Sell", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_persist_dir = "/app/persist"
if os.path.isdir(_persist_dir):
    photos_dir = os.path.join(_persist_dir, "photos")
else:
    photos_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "photos")
os.makedirs(photos_dir, exist_ok=True)
app.mount("/photos", StaticFiles(directory=photos_dir), name="photos")


# --- Health ---

@app.get("/api/health")
def health():
    return {"status": "ok"}


# --- Listings ---

@app.post("/api/listings", status_code=201)
def create_listing(data: models.ListingCreate):
    lid = models.create_listing(data, _get_db_path())
    listing = models.get_listing(lid, _get_db_path())
    return {"id": lid, "status": listing.status}


@app.get("/api/listings")
def list_listings(status: str | None = None):
    return models.list_listings(status=status, db_path=_get_db_path())


@app.get("/api/listings/{lid}")
def get_listing(lid: int):
    listing = models.get_listing(lid, _get_db_path())
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@app.put("/api/listings/{lid}")
def update_listing(lid: int, data: models.ListingUpdate):
    ok = models.update_listing(lid, data, _get_db_path())
    if not ok:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"message": "updated"}


@app.delete("/api/listings/{lid}")
def delete_listing(lid: int):
    ok = models.delete_listing(lid, _get_db_path())
    if not ok:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"message": "deleted"}


class BatchApproveRequest(BaseModel):
    ids: list[int]


@app.post("/api/listings/batch-approve")
def batch_approve(req: BatchApproveRequest):
    count = models.batch_update_status(req.ids, "active", _get_db_path())
    return {"updated": count}


class BatchStatusRequest(BaseModel):
    ids: list[int]
    status: str


@app.post("/api/listings/batch-status")
def batch_status(req: BatchStatusRequest):
    count = models.batch_update_status(req.ids, req.status, _get_db_path())
    return {"updated": count}


# --- Marketplace (public, no min_price, excludes past-deadline) ---

def _days_remaining(deadline: str | None) -> int:
    """Calculate days remaining before a listing's deadline."""
    if not deadline:
        return 0
    try:
        dl = date.fromisoformat(deadline)
    except ValueError:
        return 0
    return max((dl - date.today()).days, 0)


@app.get("/api/marketplace")
def marketplace():
    active = models.list_listings(status="active", db_path=_get_db_path())
    sold = models.list_listings(status="sold", db_path=_get_db_path())
    listings = active + sold
    today = date.today()
    result = []
    for listing in listings:
        # Skip past-deadline listings (active only -- sold items always show).
        if listing.status == "active" and listing.deadline:
            try:
                dl = date.fromisoformat(listing.deadline)
            except ValueError:
                continue
            if dl < today:
                continue

        d = listing.model_dump()
        d.pop("min_price", None)
        d["days_remaining"] = _days_remaining(listing.deadline)
        cp = compute_current_price(
            asking_price=listing.asking_price,
            min_price=listing.min_price,
            pricing_strategy=listing.pricing_strategy or "aggressive",
            deadline=date.fromisoformat(listing.deadline) if listing.deadline else today,
        )
        d["current_price"] = cp
        photos = models.get_photos(listing.id, _get_db_path())
        d["photos"] = [f"/photos/{p.file_path}" for p in photos]
        # Mark items added within the last 2 days as "new" (for badge + top placement).
        d["is_new"] = _is_new(listing.created_at)
        result.append(d)
    result.sort(key=_marketplace_sort_key)
    return result


# How recent a listing must be to count as "new" (top bucket + badge).
_NEW_WINDOW_DAYS = 2
# Location whose items sink below everything else at "our place" (but above sold).
_SECONDARY_LOCATION = "700 7th St SW"  # Ashton's mom's place


def _is_new(created_at: str | None) -> bool:
    """True if the listing was added within the last _NEW_WINDOW_DAYS days."""
    if not created_at:
        return False
    try:
        created = datetime.fromisoformat(created_at).date()
    except ValueError:
        return False
    return created >= date.today() - timedelta(days=_NEW_WINDOW_DAYS)


def _marketplace_sort_key(d: dict):
    """Merchandising order, top of page to bottom:

    1. Sold items pinned to the absolute bottom.
    2. New items (added in the last 2 days) bubble to the top.
    3. "Our place" (800 4th St SW / SW DC) above Ashton's mom's (700 7th St SW).
    4. Bulky items above smaller items.
    5. Newest first within each tier (so old stock -- e.g. the bikes -- sinks).
    """
    is_sold = 1 if d.get("status") == "sold" else 0
    is_new = 0 if d.get("is_new") else 1
    is_secondary = 1 if d.get("location") == _SECONDARY_LOCATION else 0
    not_bulky = 0 if d.get("bulky") else 1
    # Newer = higher: sort ascending on a reversed timestamp string.
    created = d.get("created_at") or ""
    newest_first = tuple(-ord(c) for c in created)
    return (is_sold, is_new, is_secondary, not_bulky, newest_first)


# --- Friends Marketplace (price-free variant; excludes flagged items) ---

# Fields removed for friends: prices, deadlines/discounting signals, share, comps.
_FRIENDS_STRIP_FIELDS = (
    "asking_price",
    "min_price",
    "original_price",
    "price_comps",
    "share_url",
    "pricing_strategy",
)


@app.get("/api/friends-marketplace")
def friends_marketplace():
    active = models.list_listings(status="active", db_path=_get_db_path())
    today = date.today()
    result = []
    for listing in active:
        if listing.friends_excluded:
            continue
        if listing.deadline:
            try:
                dl = date.fromisoformat(listing.deadline)
            except ValueError:
                continue
            if dl < today:
                continue
        d = listing.model_dump()
        for k in _FRIENDS_STRIP_FIELDS:
            d.pop(k, None)
        photos = models.get_photos(listing.id, _get_db_path())
        d["photos"] = [f"/photos/{p.file_path}" for p in photos]
        result.append(d)
    return result


# --- Meeting Spots ---

@app.get("/api/meeting-spots")
def meeting_spots():
    return [spot_to_dict(s) for s in get_all_spots()]


# --- Offers ---

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


@app.get("/api/listings/{lid}/offers")
def list_offers(lid: int):
    listing = models.get_listing(lid, _get_db_path())
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return models.list_offers(listing_id=lid, db_path=_get_db_path())


# --- Photos ---

@app.post("/api/listings/{lid}/photos", status_code=201)
def upload_photo(lid: int, file: UploadFile):
    listing = models.get_listing(lid, _get_db_path())
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    photos_base = photos_dir

    # Save file with unique name
    ext = os.path.splitext(file.filename or "photo.jpg")[1] or ".jpg"
    filename = f"{lid}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(photos_base, filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Check if this is the first photo (make it primary)
    existing = models.get_photos(lid, _get_db_path())
    is_primary = len(existing) == 0

    photo_id = models.add_photo(lid, filename, is_primary, _get_db_path())
    return {"id": photo_id, "file_path": filename, "url": f"/photos/{filename}"}


@app.get("/api/listings/{lid}/photos")
def list_photos(lid: int):
    listing = models.get_listing(lid, _get_db_path())
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    photos = models.get_photos(lid, _get_db_path())
    return [{"id": p.id, "url": f"/photos/{p.file_path}", "is_primary": p.is_primary} for p in photos]


@app.delete("/api/listings/{lid}/photos/{pid}", status_code=204)
def delete_listing_photo(lid: int, pid: int):
    listing = models.get_listing(lid, _get_db_path())
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    existing = models.get_photo(pid, _get_db_path())
    if existing is None or existing.listing_id != lid:
        raise HTTPException(status_code=404, detail="Photo not found")
    file_path = models.delete_photo(pid, _get_db_path())
    if file_path:
        try:
            os.remove(os.path.join(photos_dir, file_path))
        except FileNotFoundError:
            pass


# --- External Posts ---

@app.get("/api/listings/{lid}/external-posts")
def list_external_posts_for_listing(lid: int):
    from backend.external_posts import list_external_posts
    listing = models.get_listing(lid, _get_db_path())
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    return list_external_posts(listing_id=lid, db_path=_get_db_path())


class ExternalPostCreate(BaseModel):
    platform: str
    url: str | None = None
    last_price_posted: float | None = None


@app.post("/api/listings/{lid}/external-posts", status_code=201)
def create_external_post_for_listing(lid: int, data: ExternalPostCreate):
    from backend.external_posts import create_external_post, list_external_posts
    listing = models.get_listing(lid, _get_db_path())
    if listing is None:
        raise HTTPException(status_code=404, detail="Listing not found")
    pid = create_external_post(
        listing_id=lid,
        platform=data.platform,
        url=data.url,
        last_price_posted=data.last_price_posted,
        db_path=_get_db_path(),
    )
    posts = list_external_posts(listing_id=lid, db_path=_get_db_path())
    return next(p for p in posts if p["id"] == pid)


@app.get("/api/external-posts/stale")
def get_stale_external_posts():
    from backend.external_posts import get_stale_posts
    return get_stale_posts(db_path=_get_db_path())


class ExternalPostStatusUpdate(BaseModel):
    status: str


@app.put("/api/external-posts/{pid}/status")
def update_external_post_status_endpoint(pid: int, data: ExternalPostStatusUpdate):
    from backend.external_posts import list_external_posts, update_external_post_status
    changed = update_external_post_status(pid, data.status, db_path=_get_db_path())
    if not changed:
        raise HTTPException(status_code=404, detail="External post not found")
    posts = list_external_posts(db_path=_get_db_path())
    return next(p for p in posts if p["id"] == pid)


# --- Events (click/view analytics) ---

class EventCreate(BaseModel):
    event_type: str
    listing_id: int | None = None
    target: str | None = None
    session_id: str | None = None


@app.post("/api/events", status_code=201)
def create_event(data: EventCreate, request: Request):
    from backend.events import record_event

    # referrer + user-agent come from headers, never the client body, so the
    # beacon stays a one-liner and clients can't spoof these fields freely.
    ua = request.headers.get("user-agent")
    referrer = request.headers.get("referer")
    eid = record_event(
        event_type=data.event_type,
        listing_id=data.listing_id,
        target=data.target,
        referrer=referrer,
        session_id=data.session_id,
        user_agent=ua,
        db_path=_get_db_path(),
    )
    return {"id": eid}


@app.get("/api/events/summary")
def events_summary():
    """Cumulative, PII-free event counts -- the nightly snapshot source."""
    from backend.events import event_summary

    rows = event_summary(_get_db_path())
    return {
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "totals": _events_totals(rows),
        "by_listing": rows,
    }


def _events_totals(rows: list[dict]) -> dict[str, int]:
    """Roll per-(listing, type) rows up to one count per event type."""
    totals: dict[str, int] = {}
    for r in rows:
        totals[r["event_type"]] = totals.get(r["event_type"], 0) + r["count"]
    return totals


# --- Static file serving (production) ---
# This must be LAST so it doesn't shadow API routes

from starlette.responses import FileResponse

_project_root = os.path.dirname(os.path.dirname(__file__))
showcase_dir = os.path.join(_project_root, "showcase")
showcase_index = os.path.join(showcase_dir, "index.html")
if os.path.isdir(showcase_dir):
    app.mount("/showcase", StaticFiles(directory=showcase_dir, html=True), name="showcase")

frontend_dist = os.path.join(_project_root, "frontend", "dist")
if os.path.isdir(frontend_dist) or os.path.isdir(showcase_dir):
    @app.get("/{path:path}")
    def spa_fallback(path: str):
        """Public face: React SPA (the redesign). Showcase remains at /showcase."""
        # Prefer the React SPA dist for everything (root + sub-routes).
        if os.path.isdir(frontend_dist):
            file_path = os.path.join(frontend_dist, path)
            if path and os.path.isfile(file_path):
                return FileResponse(file_path)
            index = os.path.join(frontend_dist, "index.html")
            if os.path.exists(index):
                return FileResponse(index)
        # No SPA dist? Fall back to showcase.
        if os.path.isfile(showcase_index):
            return FileResponse(showcase_index)
        raise HTTPException(status_code=404, detail="Not found")
