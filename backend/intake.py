from __future__ import annotations
import re
from dataclasses import dataclass, field


@dataclass
class GeminiItem:
    title: str
    description: str | None = None
    category: str | None = None
    condition: str | None = None
    original_price: float | None = None
    purchase_date: str | None = None
    purchase_source: str | None = None


# Category detection keywords
CATEGORY_KEYWORDS = {
    "electronics": ["monitor", "tv", "laptop", "computer", "tablet", "phone", "camera", "kindle", "ipad"],
    "audio": ["headphones", "earbuds", "speaker", "airpods", "soundbar", "amplifier"],
    "furniture": ["desk", "chair", "table", "shelf", "bookcase", "cabinet", "dresser", "sofa", "couch", "bed"],
    "fitness": ["dumbbell", "weight", "treadmill", "bike", "yoga", "bench", "kettlebell", "bowflex"],
}

# Depreciation rates: asking = (1 - rate) * original
DEPRECIATION_RATES = {
    "electronics": 0.55,
    "furniture": 0.35,
    "fitness": 0.40,
    "audio": 0.50,
}
DEFAULT_DEPRECIATION = 0.50
MIN_PRICE_RATIO = 0.70  # min_price = 70% of asking


CONDITION_PATTERNS = [
    "like new", "excellent", "very good", "good", "fair", "poor",
]

SOURCES = [
    "Amazon", "Best Buy", "IKEA", "Walmart", "Target", "Costco",
    "Apple", "B&H", "Newegg", "office liquidator", "Wayfair",
    "Home Depot", "Lowe's",
]


def _detect_category(title: str) -> str | None:
    lower = title.lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return cat
    return None


def _extract_condition(text: str) -> str | None:
    lower = text.lower()
    for cond in CONDITION_PATTERNS:
        if cond in lower:
            return cond
    return None


def _extract_price(text: str) -> float | None:
    match = re.search(r"\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", text)
    if match:
        return float(match.group(1).replace(",", ""))
    return None


def _extract_date(text: str) -> str | None:
    match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if match:
        return match.group(1)
    # Try "Month DD, YYYY" or other patterns
    match = re.search(
        r"dated\s+(\d{4}-\d{2}-\d{2})", text
    )
    if match:
        return match.group(1)
    return None


def _extract_source(text: str) -> str | None:
    lower = text.lower()
    for source in SOURCES:
        if source.lower() in lower:
            return source
    return None


def parse_gemini_response(text: str) -> list[GeminiItem]:
    if not text or not text.strip():
        return []

    # Split on numbered items: "1. **Title**" pattern
    pattern = r"\d+\.\s+\*\*(.+?)\*\*\s*[-–—]\s*(.+?)(?=\n\d+\.\s+\*\*|\Z)"
    matches = re.findall(pattern, text, re.DOTALL)

    if not matches:
        return []

    items = []
    for title, body in matches:
        title = title.strip()
        body = body.strip()
        category = _detect_category(title)
        condition = _extract_condition(body)
        original_price = _extract_price(body)
        purchase_date = _extract_date(body)
        purchase_source = _extract_source(body)

        # Clean description: first sentence before receipt info
        desc_match = re.match(r"^(.+?)(?:\.\s*(?:I found|Receipt|No receipt))", body)
        description = desc_match.group(1).strip() if desc_match else body.split(".")[0].strip()

        items.append(GeminiItem(
            title=title,
            description=description,
            category=category,
            condition=condition,
            original_price=original_price,
            purchase_date=purchase_date,
            purchase_source=purchase_source,
        ))

    return items


def suggest_prices(item: GeminiItem) -> tuple[float | None, float | None]:
    if item.original_price is None:
        return None, None

    category = item.category or "other"
    rate = DEPRECIATION_RATES.get(category, DEFAULT_DEPRECIATION)
    asking = round(item.original_price * (1 - rate), 2)
    minimum = round(asking * MIN_PRICE_RATIO, 2)
    return asking, minimum
