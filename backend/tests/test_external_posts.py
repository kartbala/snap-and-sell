"""Tests for external posts CRUD."""
import pytest
from backend.database import init_db
from backend.models import ListingCreate, create_listing
from backend.external_posts import (
    create_external_post, list_external_posts,
    update_external_post_status, get_stale_posts,
)

@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path

@pytest.fixture
def listing_ids(db_path):
    """Create two listings to satisfy foreign key constraints."""
    lid1 = create_listing(ListingCreate(title="Item A", asking_price=50.0), db_path)
    lid2 = create_listing(ListingCreate(title="Item B", asking_price=80.0), db_path)
    return lid1, lid2


def test_create_and_list(db_path, listing_ids):
    lid1, _ = listing_ids
    pid = create_external_post(
        listing_id=lid1, platform="craigslist",
        url="https://craigslist.org/123", last_price_posted=50.0,
        db_path=db_path,
    )
    assert pid > 0
    posts = list_external_posts(listing_id=lid1, db_path=db_path)
    assert len(posts) == 1
    assert posts[0]["platform"] == "craigslist"
    assert posts[0]["status"] == "active"


def test_update_status(db_path, listing_ids):
    lid1, _ = listing_ids
    pid = create_external_post(listing_id=lid1, platform="facebook", db_path=db_path)
    update_external_post_status(pid, "price_stale", db_path=db_path)
    posts = list_external_posts(listing_id=lid1, db_path=db_path)
    assert posts[0]["status"] == "price_stale"


def test_get_stale_posts(db_path, listing_ids):
    lid1, lid2 = listing_ids
    pid1 = create_external_post(listing_id=lid1, platform="craigslist", db_path=db_path)
    pid2 = create_external_post(listing_id=lid2, platform="facebook", db_path=db_path)
    update_external_post_status(pid1, "price_stale", db_path=db_path)
    stale = get_stale_posts(db_path=db_path)
    assert len(stale) == 1
    assert stale[0]["id"] == pid1


def test_list_by_platform(db_path, listing_ids):
    lid1, _ = listing_ids
    create_external_post(listing_id=lid1, platform="craigslist", db_path=db_path)
    create_external_post(listing_id=lid1, platform="facebook", db_path=db_path)
    cl = list_external_posts(listing_id=lid1, platform="craigslist", db_path=db_path)
    assert len(cl) == 1
    assert cl[0]["platform"] == "craigslist"
