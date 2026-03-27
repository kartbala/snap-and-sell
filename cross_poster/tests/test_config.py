"""Tests for config loading and category mapping."""
import json
import os
import tempfile
from cross_poster.config import (
    load_listings_from_json,
    map_category_cl,
    map_category_fb,
    resolve_photo_paths,
    Listing,
)


def test_map_category_cl_known():
    assert map_category_cl("electronics") == "electronics"
    assert map_category_cl("fitness") == "sporting goods"
    assert map_category_cl("furniture") == "furniture"
    assert map_category_cl("bikes") == "bicycles"


def test_map_category_cl_unknown_passes_through():
    assert map_category_cl("toys") == "general for sale"


def test_map_category_fb_known():
    assert map_category_fb("electronics") == "Electronics"
    assert map_category_fb("fitness") == "Sporting Goods"
    assert map_category_fb("furniture") == "Home & Garden"
    assert map_category_fb("bikes") == "Bicycles"


def test_map_category_fb_unknown_passes_through():
    assert map_category_fb("toys") == "Miscellaneous"


def test_load_listings_from_json():
    data = [
        {
            "title": "Test Item",
            "price": 100,
            "description": "A test item",
            "category": "electronics",
            "location": "SW DC",
            "zip": "20024",
            "photos": ["/tmp/photo1.jpg"],
            "platforms": ["craigslist"],
        }
    ]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(data, f)
        f.flush()
        listings = load_listings_from_json(f.name)

    assert len(listings) == 1
    assert listings[0].title == "Test Item"
    assert listings[0].price == 100
    assert listings[0].platforms == ["craigslist"]
    os.unlink(f.name)


def test_load_listings_from_json_defaults():
    data = [
        {
            "title": "Minimal Item",
            "price": 50,
            "description": "Bare minimum",
            "category": "furniture",
        }
    ]
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(data, f)
        f.flush()
        listings = load_listings_from_json(f.name)

    assert listings[0].location == "SW Washington DC"
    assert listings[0].zip == "20024"
    assert listings[0].platforms == ["craigslist", "facebook"]
    assert listings[0].photos == []
    os.unlink(f.name)


def test_resolve_photo_paths_expands_tilde(tmp_path):
    # Create a real file inside tmp_path so filtering doesn't drop it.
    # Use a path that mimics ~/Downloads/test.jpg structure by naming the
    # file appropriately, but we pass the actual absolute path with ~ replaced.
    real_file = tmp_path / "test.jpg"
    real_file.write_bytes(b"fake jpeg")

    # Patch the home dir to tmp_path so "~" expands into our tmp dir.
    import unittest.mock as mock
    with mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", str(tmp_path))):
        paths = resolve_photo_paths(["~/test.jpg"])

    assert len(paths) == 1
    assert not paths[0].startswith("~")
    assert "test.jpg" in paths[0]


def test_resolve_photo_paths_filters_missing(tmp_path):
    real_file = tmp_path / "exists.jpg"
    real_file.write_bytes(b"fake jpeg")
    paths = resolve_photo_paths(
        [str(real_file), "/nonexistent/fake.jpg"]
    )
    assert len(paths) == 1
    assert paths[0] == str(real_file)
