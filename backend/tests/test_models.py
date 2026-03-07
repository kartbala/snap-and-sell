import os
import tempfile
import pytest
from backend.database import init_db
from backend import models


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


class TestListingsCRUD:
    def test_create_listing(self, db_path):
        data = models.ListingCreate(
            title="IKEA Desk", description="Standing desk", category="furniture",
            condition="good", asking_price=150.0, min_price=100.0,
        )
        lid = models.create_listing(data, db_path)
        assert lid == 1

    def test_get_listing(self, db_path):
        data = models.ListingCreate(title="Desk", asking_price=150.0)
        lid = models.create_listing(data, db_path)
        listing = models.get_listing(lid, db_path)
        assert listing is not None
        assert listing.title == "Desk"
        assert listing.asking_price == 150.0
        assert listing.status == "draft"

    def test_get_listing_not_found(self, db_path):
        assert models.get_listing(999, db_path) is None

    def test_list_listings_all(self, db_path):
        models.create_listing(models.ListingCreate(title="A", asking_price=10), db_path)
        models.create_listing(models.ListingCreate(title="B", asking_price=20), db_path)
        listings = models.list_listings(db_path=db_path)
        assert len(listings) == 2

    def test_list_listings_by_status(self, db_path):
        models.create_listing(models.ListingCreate(title="A", asking_price=10), db_path)
        lid2 = models.create_listing(models.ListingCreate(title="B", asking_price=20), db_path)
        models.update_listing(lid2, models.ListingUpdate(status="active"), db_path)
        drafts = models.list_listings(status="draft", db_path=db_path)
        active = models.list_listings(status="active", db_path=db_path)
        assert len(drafts) == 1
        assert len(active) == 1

    def test_update_listing(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Old", asking_price=10), db_path
        )
        ok = models.update_listing(lid, models.ListingUpdate(title="New", asking_price=20), db_path)
        assert ok is True
        listing = models.get_listing(lid, db_path)
        assert listing.title == "New"
        assert listing.asking_price == 20.0

    def test_update_listing_not_found(self, db_path):
        ok = models.update_listing(999, models.ListingUpdate(title="X"), db_path)
        assert ok is False

    def test_delete_listing(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Del", asking_price=10), db_path
        )
        ok = models.delete_listing(lid, db_path)
        assert ok is True
        assert models.get_listing(lid, db_path) is None

    def test_delete_listing_not_found(self, db_path):
        assert models.delete_listing(999, db_path) is False

    def test_batch_update_status(self, db_path):
        id1 = models.create_listing(models.ListingCreate(title="A", asking_price=10), db_path)
        id2 = models.create_listing(models.ListingCreate(title="B", asking_price=20), db_path)
        id3 = models.create_listing(models.ListingCreate(title="C", asking_price=30), db_path)
        count = models.batch_update_status([id1, id2], "active", db_path)
        assert count == 2
        assert models.get_listing(id1, db_path).status == "active"
        assert models.get_listing(id2, db_path).status == "active"
        assert models.get_listing(id3, db_path).status == "draft"

    def test_delete_cascades_photos(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Item", asking_price=10), db_path
        )
        models.add_photo(lid, "photo.jpg", True, db_path)
        models.delete_listing(lid, db_path)
        assert models.get_photos(lid, db_path) == []

    def test_delete_cascades_offers(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Item", asking_price=10), db_path
        )
        models.create_offer(
            models.OfferCreate(
                listing_id=lid, buyer_name="Bob", buyer_phone="555-1234",
                offer_amount=8.0,
            ),
            db_path,
        )
        models.delete_listing(lid, db_path)
        assert models.list_offers(listing_id=lid, db_path=db_path) == []


class TestOffersCRUD:
    def test_create_offer(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Item", asking_price=50), db_path
        )
        oid = models.create_offer(
            models.OfferCreate(
                listing_id=lid, buyer_name="Alice", buyer_phone="555-0000",
                buyer_email="alice@example.com", offer_amount=45.0, message="Interested",
            ),
            db_path,
        )
        assert oid == 1

    def test_list_offers_for_listing(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Item", asking_price=50), db_path
        )
        models.create_offer(
            models.OfferCreate(
                listing_id=lid, buyer_name="A", buyer_phone="555", offer_amount=40,
            ),
            db_path,
        )
        models.create_offer(
            models.OfferCreate(
                listing_id=lid, buyer_name="B", buyer_phone="556", offer_amount=45,
            ),
            db_path,
        )
        offers = models.list_offers(listing_id=lid, db_path=db_path)
        assert len(offers) == 2

    def test_update_offer_status(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Item", asking_price=50), db_path
        )
        oid = models.create_offer(
            models.OfferCreate(
                listing_id=lid, buyer_name="A", buyer_phone="555", offer_amount=40,
            ),
            db_path,
        )
        ok = models.update_offer_status(oid, "accepted", "Deal!", db_path)
        assert ok is True
        offers = models.list_offers(listing_id=lid, db_path=db_path)
        assert offers[0].status == "accepted"
        assert offers[0].response_message == "Deal!"


class TestPhotosCRUD:
    def test_add_photo(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Item", asking_price=10), db_path
        )
        pid = models.add_photo(lid, "photos/item1.jpg", True, db_path)
        assert pid == 1

    def test_get_photos(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Item", asking_price=10), db_path
        )
        models.add_photo(lid, "photos/a.jpg", True, db_path)
        models.add_photo(lid, "photos/b.jpg", False, db_path)
        photos = models.get_photos(lid, db_path)
        assert len(photos) == 2
        assert photos[0].is_primary is True
        assert photos[1].is_primary is False
