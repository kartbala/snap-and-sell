"""Edge case tests for Gemini intake parser."""

import pytest
from backend.intake import parse_gemini_response, suggest_prices, GeminiItem, _detect_category


# Text with unusual formatting
MESSY_TEXT = """
Here's what I found in your photos:

1. **Apple AirPods Pro (2nd Gen)** - White wireless earbuds with MagSafe charging case, good condition. I found a receipt from Amazon dated 2024-01-05 for $249.00.

2. **LG 55" OLED TV (C3)** - 55 inch OLED 4K Smart TV, like new condition. Receipt from Best Buy dated 2023-12-01 for $1,299.99.

3. **Peloton Bike+** - Indoor cycling bike with screen, good condition. Receipt from Peloton dated 2022-06-20 for $2,495.00.
"""

# Text with comma-separated prices
COMMA_PRICE_TEXT = """
1. **Gaming PC Build** - Custom gaming computer, excellent condition. Receipt from Newegg dated 2024-03-01 for $1,899.99.
"""

# Text with only one item and minimal info
MINIMAL_TEXT = """
1. **Random Box of Stuff** - Miscellaneous items, fair condition. No receipt found.
"""

# Text with no bold formatting (should return empty)
NO_BOLD_TEXT = """
I found some items:
1. A desk lamp - good condition, $30
2. A keyboard - fair condition, $50
"""

# Text with special characters in titles
SPECIAL_CHARS_TEXT = """
1. **Samsung 27" Monitor (S27R750) - 4K/UHD** - Great monitor for work. Receipt from Amazon dated 2024-02-15 for $449.99.
"""


class TestParseEdgeCases:
    def test_comma_separated_price(self):
        items = parse_gemini_response(COMMA_PRICE_TEXT)
        assert len(items) == 1
        assert items[0].original_price == 1899.99

    def test_large_price(self):
        items = parse_gemini_response(MESSY_TEXT)
        tv = items[1]
        assert tv.original_price == 1299.99
        peloton = items[2]
        assert peloton.original_price == 2495.00

    def test_minimal_item(self):
        items = parse_gemini_response(MINIMAL_TEXT)
        assert len(items) == 1
        assert items[0].title == "Random Box of Stuff"
        assert items[0].original_price is None
        assert items[0].condition == "fair"

    def test_no_bold_returns_empty(self):
        items = parse_gemini_response(NO_BOLD_TEXT)
        assert items == []

    def test_whitespace_only(self):
        items = parse_gemini_response("   \n\n  \t  ")
        assert items == []

    def test_special_chars_in_title(self):
        items = parse_gemini_response(SPECIAL_CHARS_TEXT)
        assert len(items) == 1
        assert '27"' in items[0].title

    def test_condition_like_new(self):
        items = parse_gemini_response(MESSY_TEXT)
        assert items[1].condition == "like new"

    def test_source_peloton_not_detected(self):
        """Peloton isn't in our source list — should be None."""
        items = parse_gemini_response(MESSY_TEXT)
        peloton = items[2]
        # "Peloton" isn't in SOURCES list
        assert peloton.purchase_source is None

    def test_source_best_buy(self):
        items = parse_gemini_response(MESSY_TEXT)
        assert items[1].purchase_source == "Best Buy"

    def test_date_extraction(self):
        items = parse_gemini_response(MESSY_TEXT)
        assert items[0].purchase_date == "2024-01-05"
        assert items[1].purchase_date == "2023-12-01"

    def test_description_extracted(self):
        items = parse_gemini_response(MESSY_TEXT)
        assert items[0].description is not None
        assert len(items[0].description) > 0


class TestCategoryDetection:
    def test_tv_is_electronics(self):
        assert _detect_category("LG 55 OLED TV") == "electronics"

    def test_airpods_is_audio(self):
        assert _detect_category("Apple AirPods Pro") == "audio"

    def test_desk_is_furniture(self):
        assert _detect_category("Standing Desk") == "furniture"

    def test_dumbbells_is_fitness(self):
        assert _detect_category("Bowflex Dumbbells") == "fitness"

    def test_unknown_is_none(self):
        assert _detect_category("Random Thing") is None

    def test_case_insensitive(self):
        assert _detect_category("SAMSUNG MONITOR") == "electronics"
        assert _detect_category("ikea BOOKCASE") == "furniture"


class TestSuggestPricesEdgeCases:
    def test_very_cheap_item(self):
        item = GeminiItem(title="Cable", category="electronics", original_price=5.0)
        asking, minimum = suggest_prices(item)
        assert asking == 2.25  # 45% of 5
        assert minimum == 1.57  # 70% of 2.25 = 1.575, rounds to 1.57

    def test_very_expensive_item(self):
        item = GeminiItem(title="Server", category="electronics", original_price=10000.0)
        asking, minimum = suggest_prices(item)
        assert asking == 4500.0
        assert minimum == 3150.0

    def test_zero_price(self):
        item = GeminiItem(title="Free", category="electronics", original_price=0.0)
        asking, minimum = suggest_prices(item)
        assert asking == 0.0
        assert minimum == 0.0

    def test_none_category_uses_default(self):
        item = GeminiItem(title="Mystery", original_price=100.0)
        asking, minimum = suggest_prices(item)
        assert asking == 50.0  # default 50%
        assert minimum == 35.0

    def test_all_categories_produce_valid_prices(self):
        for cat in ["electronics", "audio", "furniture", "fitness", "other", None]:
            item = GeminiItem(title="Test", category=cat, original_price=200.0)
            asking, minimum = suggest_prices(item)
            assert asking is not None
            assert minimum is not None
            assert 0 <= minimum <= asking <= 200.0
