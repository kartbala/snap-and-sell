"""Rebrandly share link generation."""
from __future__ import annotations
import json
import os
import re
import urllib.request


REBRANDLY_API_KEY = os.environ.get("REBRANDLY_API_KEY", "")
REBRANDLY_DOMAIN = "karthik.link"
REBRANDLY_API_URL = "https://api.rebrandly.com/v1/links"


def generate_slashtag(title: str) -> str:
    """Generate a URL-safe slashtag from a listing title."""
    if not title.strip():
        import random
        return f"item-{random.randint(1000, 9999)}"
    slug = title.lower()
    slug = re.sub(r"[\"'()\[\]{}]", "", slug)
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:50]


def _call_rebrandly(payload: dict) -> dict:
    """Make a POST request to Rebrandly API."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        REBRANDLY_API_URL,
        data=data,
        headers={
            "Content-Type": "application/json",
            "apikey": REBRANDLY_API_KEY,
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def create_short_link(
    title: str, listing_id: int,
    base_url: str = os.environ.get("BASE_URL", "http://localhost:5173"),
) -> str | None:
    """Create a Rebrandly short link for a listing. Returns URL or None on failure."""
    payload = {
        "destination": f"{base_url}/?item={listing_id}",
        "slashtag": generate_slashtag(title),
        "domain": {"fullName": REBRANDLY_DOMAIN},
    }
    try:
        result = _call_rebrandly(payload)
        return result.get("shortUrl") or f"https://{REBRANDLY_DOMAIN}/{result.get('slashtag', '')}"
    except Exception:
        return None
