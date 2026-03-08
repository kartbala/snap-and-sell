from __future__ import annotations
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from functools import lru_cache
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from backend.database import init_db, DEFAULT_DB_PATH
from backend import models
from backend.meeting_spots import get_all_spots, suggest_spot, spot_to_dict

LISTING_EXPIRY_DAYS = 30


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

photos_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "photos")
if os.path.isdir(photos_dir):
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


# --- Marketplace (public, no min_price, excludes expired) ---

def _days_remaining(created_at: str) -> int:
    """Calculate days remaining before a listing expires."""
    try:
        created = datetime.fromisoformat(created_at)
    except ValueError:
        created = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    expiry = created + timedelta(days=LISTING_EXPIRY_DAYS)
    remaining = (expiry - datetime.now()).days
    return max(remaining, 0)


@app.get("/api/marketplace")
def marketplace():
    listings = models.list_listings(status="active", db_path=_get_db_path())
    cutoff = datetime.now() - timedelta(days=LISTING_EXPIRY_DAYS)
    result = []
    for listing in listings:
        try:
            created = datetime.fromisoformat(listing.created_at)
        except ValueError:
            created = datetime.strptime(listing.created_at, "%Y-%m-%d %H:%M:%S")
        if created < cutoff:
            continue
        d = listing.model_dump()
        d.pop("min_price", None)
        d["days_remaining"] = _days_remaining(listing.created_at)
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

    oid = models.create_offer(data, _get_db_path())
    result = evaluate_offer(data.offer_amount, listing.asking_price, listing.min_price)
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
