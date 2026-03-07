import pytest
from backend.intake import parse_gemini_response, suggest_prices, GeminiItem


SINGLE_ITEM_TEXT = """
Here's what I found:

1. **Sony WH-1000XM5 Headphones** - Over-ear noise canceling headphones, black color, excellent condition. I found a receipt from Amazon dated 2024-06-15 for $349.99.
"""

BATCH_TEXT = """
I identified the following items from your photos:

1. **Samsung 27" Monitor (S27R750)** - 27 inch 4K monitor, space gray, good condition. Receipt from Best Buy dated 2023-11-20 for $449.99.

2. **IKEA BEKANT Standing Desk** - Electric sit/stand desk, white, 63x31 inches, good condition. Receipt from IKEA dated 2023-03-10 for $549.00.

3. **Bowflex SelectTech 552 Dumbbells** - Adjustable dumbbells, pair, like new condition. No receipt found.

4. **Apple AirPods Pro (2nd Gen)** - Wireless earbuds with case, white, good condition. Receipt from Amazon dated 2024-01-05 for $249.00.

5. **Herman Miller Aeron Chair** - Size B, graphite, excellent condition. Receipt from office liquidator dated 2022-08-15 for $899.00.
"""

NO_ITEMS_TEXT = """
I looked through your photos but couldn't identify any items for sale. The photos appear to be landscape shots.
"""

EMPTY_TEXT = ""


class TestParseGeminiResponse:
    def test_single_item(self):
        items = parse_gemini_response(SINGLE_ITEM_TEXT)
        assert len(items) == 1
        item = items[0]
        assert item.title == "Sony WH-1000XM5 Headphones"
        assert item.original_price == 349.99
        assert item.purchase_source == "Amazon"
        assert item.purchase_date == "2024-06-15"

    def test_batch_parse(self):
        items = parse_gemini_response(BATCH_TEXT)
        assert len(items) == 5
        assert items[0].title == 'Samsung 27" Monitor (S27R750)'
        assert items[1].title == "IKEA BEKANT Standing Desk"
        assert items[3].original_price == 249.00

    def test_missing_receipt(self):
        items = parse_gemini_response(BATCH_TEXT)
        dumbbells = items[2]
        assert dumbbells.title == "Bowflex SelectTech 552 Dumbbells"
        assert dumbbells.original_price is None
        assert dumbbells.purchase_source is None
        assert dumbbells.purchase_date is None

    def test_no_items(self):
        items = parse_gemini_response(NO_ITEMS_TEXT)
        assert items == []

    def test_empty_text(self):
        items = parse_gemini_response(EMPTY_TEXT)
        assert items == []

    def test_price_extraction(self):
        items = parse_gemini_response(BATCH_TEXT)
        assert items[0].original_price == 449.99
        assert items[1].original_price == 549.00
        assert items[4].original_price == 899.00

    def test_condition_extraction(self):
        items = parse_gemini_response(BATCH_TEXT)
        assert items[0].condition == "good"
        assert items[2].condition == "like new"
        assert items[4].condition == "excellent"


class TestSuggestPrices:
    def test_electronics_depreciation(self):
        item = GeminiItem(
            title="Monitor", category="electronics", original_price=400.0,
        )
        asking, minimum = suggest_prices(item)
        assert asking == 180.0  # 45% of 400
        assert minimum == 126.0  # 70% of asking

    def test_furniture_depreciation(self):
        item = GeminiItem(
            title="Desk", category="furniture", original_price=500.0,
        )
        asking, minimum = suggest_prices(item)
        assert asking == 325.0  # 65% of 500
        assert minimum == 227.5  # 70% of asking

    def test_fitness_depreciation(self):
        item = GeminiItem(
            title="Dumbbells", category="fitness", original_price=300.0,
        )
        asking, minimum = suggest_prices(item)
        assert asking == 180.0  # 60% of 300
        assert minimum == 126.0  # 70% of asking

    def test_audio_depreciation(self):
        item = GeminiItem(
            title="Headphones", category="audio", original_price=350.0,
        )
        asking, minimum = suggest_prices(item)
        assert asking == 175.0  # 50% of 350
        assert minimum == 122.5  # 70% of asking

    def test_no_original_price(self):
        item = GeminiItem(title="Unknown Item")
        asking, minimum = suggest_prices(item)
        assert asking is None
        assert minimum is None

    def test_default_category(self):
        item = GeminiItem(
            title="Random Thing", category="other", original_price=100.0,
        )
        asking, minimum = suggest_prices(item)
        assert asking == 50.0  # 50% default
        assert minimum == 35.0

    def test_prices_within_bounds(self):
        item = GeminiItem(
            title="Expensive Item", category="electronics", original_price=2000.0,
        )
        asking, minimum = suggest_prices(item)
        assert asking <= 2000.0
        assert minimum <= asking
        assert minimum > 0
