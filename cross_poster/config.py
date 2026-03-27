"""Load listings from Snap & Sell API or JSON fallback."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

import requests

CL_CATEGORY_MAP = {
    "electronics": "electronics",
    "fitness": "sporting goods",
    "furniture": "furniture",
    "bikes": "bicycles",
    "audio": "electronics",
}

FB_CATEGORY_MAP = {
    "electronics": "Electronics",
    "fitness": "Sporting Goods",
    "furniture": "Home & Garden",
    "bikes": "Bicycles",
    "audio": "Electronics",
}


@dataclass
class Listing:
    title: str
    price: float
    description: str
    category: str
    location: str = "SW Washington DC"
    zip: str = "20024"
    photos: list[str] = field(default_factory=list)
    platforms: list[str] = field(
        default_factory=lambda: ["craigslist", "facebook"]
    )
    listing_id: int | None = None


def map_category_cl(category: str) -> str:
    return CL_CATEGORY_MAP.get(category, "general for sale")


def map_category_fb(category: str) -> str:
    return FB_CATEGORY_MAP.get(category, "Miscellaneous")


def resolve_photo_paths(paths: list[str]) -> list[str]:
    resolved = []
    for p in paths:
        expanded = os.path.expanduser(p)
        if os.path.isfile(expanded):
            resolved.append(expanded)
    return resolved


def load_listings_from_json(path: str) -> list[Listing]:
    with open(path) as f:
        data = json.load(f)
    listings = []
    for item in data:
        listings.append(
            Listing(
                title=item["title"],
                price=item["price"],
                description=item["description"],
                category=item["category"],
                location=item.get("location", "SW Washington DC"),
                zip=item.get("zip", "20024"),
                photos=item.get("photos", []),
                platforms=item.get(
                    "platforms", ["craigslist", "facebook"]
                ),
            )
        )
    return listings


def load_listings_from_api(
    base_url: str = "http://localhost:5001",
) -> list[Listing]:
    resp = requests.get(f"{base_url}/api/marketplace", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    listings = []
    for item in data:
        photo_paths = []
        if item.get("photos"):
            os.makedirs("/tmp/cross_poster_photos", exist_ok=True)
            for photo in item["photos"]:
                filename = photo["filename"]
                photo_url = f"{base_url}/photos/{filename}"
                local_path = f"/tmp/cross_poster_photos/{filename}"
                if not os.path.isfile(local_path):
                    img_resp = requests.get(photo_url, timeout=10)
                    img_resp.raise_for_status()
                    with open(local_path, "wb") as pf:
                        pf.write(img_resp.content)
                photo_paths.append(local_path)
        listings.append(
            Listing(
                title=item["title"],
                price=item.get("current_price", item["asking_price"]),
                description=item.get("description", ""),
                category=item.get("category", "general"),
                location=item.get("location", "SW Washington DC"),
                zip="20024",
                photos=photo_paths,
                listing_id=item["id"],
            )
        )
    return listings


def load_listings(
    json_path: str | None = None,
    api_url: str = "http://localhost:5001",
) -> list[Listing]:
    if json_path is None:
        json_path = os.path.join(
            os.path.dirname(__file__), "listings.json"
        )
    try:
        listings = load_listings_from_api(api_url)
        if listings:
            return listings
    except Exception:
        pass
    if os.path.isfile(json_path):
        return load_listings_from_json(json_path)
    return []
