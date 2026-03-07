"""Edge case tests for CRUD models layer."""

import os
import tempfile
import pytest
from backend.database import init_db, get_connection
from backend import models


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    os.unlink(path)


class TestListingDefaults:
    def test_default_status_is_draft(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="X", asking_price=10), db_path)
        listing = models.get_listing(lid, db_path)
        assert listing.status == "draft"

    def test_created_at_populated(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="X", asking_price=10), db_path)
        listing = models.get_listing(lid, db_path)
        assert listing.created_at is not None
        assert len(listing.created_at) > 0

    def test_updated_at_populated(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="X", asking_price=10), db_path)
        listing = models.get_listing(lid, db_path)
        assert listing.updated_at is not None

    def test_nullable_fields_default_none(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Minimal"), db_path)
        listing = models.get_listing(lid, db_path)
        assert listing.description is None
        assert listing.category is None
        assert listing.condition is None
        assert listing.asking_price is None
        assert listing.min_price is None
        assert listing.original_price is None
        assert listing.purchase_date is None
        assert listing.purchase_source is None
        assert listing.location is None


class TestUpdateEdgeCases:
    def test_update_with_no_fields(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Original", asking_price=100), db_path
        )
        result = models.update_listing(lid, models.ListingUpdate(), db_path)
        assert result is False  # No fields to update
        listing = models.get_listing(lid, db_path)
        assert listing.title == "Original"

    def test_update_sets_updated_at(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Before", asking_price=100), db_path
        )
        before = models.get_listing(lid, db_path).updated_at
        models.update_listing(lid, models.ListingUpdate(title="After"), db_path)
        after = models.get_listing(lid, db_path).updated_at
        assert after >= before

    def test_update_single_field_preserves_others(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(
                title="Item", description="Desc", category="electronics",
                asking_price=100, min_price=70,
            ),
            db_path,
        )
        models.update_listing(lid, models.ListingUpdate(title="New Title"), db_path)
        listing = models.get_listing(lid, db_path)
        assert listing.title == "New Title"
        assert listing.description == "Desc"
        assert listing.category == "electronics"
        assert listing.asking_price == 100.0
        assert listing.min_price == 70.0

    def test_update_price_to_zero(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Item", asking_price=100), db_path
        )
        # Note: 0 is falsy, so ListingUpdate needs to handle this
        # With current impl using `v is not None`, 0 should work
        models.update_listing(lid, models.ListingUpdate(asking_price=0.0), db_path)
        listing = models.get_listing(lid, db_path)
        assert listing.asking_price == 0.0


class TestListingLifecycle:
    def test_draft_to_active_to_sold(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Widget", asking_price=50), db_path
        )
        assert models.get_listing(lid, db_path).status == "draft"

        models.update_listing(lid, models.ListingUpdate(status="active"), db_path)
        assert models.get_listing(lid, db_path).status == "active"

        models.update_listing(lid, models.ListingUpdate(status="sold"), db_path)
        assert models.get_listing(lid, db_path).status == "sold"

    def test_sold_back_to_active(self, db_path):
        """Re-listing a sold item."""
        lid = models.create_listing(
            models.ListingCreate(title="Widget", asking_price=50), db_path
        )
        models.batch_update_status([lid], "active", db_path)
        models.update_listing(lid, models.ListingUpdate(status="sold"), db_path)
        models.update_listing(lid, models.ListingUpdate(status="active"), db_path)
        assert models.get_listing(lid, db_path).status == "active"

    def test_listing_count_by_status(self, db_path):
        for i in range(3):
            models.create_listing(models.ListingCreate(title=f"D{i}", asking_price=10), db_path)
        for i in range(2):
            lid = models.create_listing(models.ListingCreate(title=f"A{i}", asking_price=20), db_path)
            models.update_listing(lid, models.ListingUpdate(status="active"), db_path)
        lid = models.create_listing(models.ListingCreate(title="S0", asking_price=30), db_path)
        models.update_listing(lid, models.ListingUpdate(status="sold"), db_path)

        assert len(models.list_listings(status="draft", db_path=db_path)) == 3
        assert len(models.list_listings(status="active", db_path=db_path)) == 2
        assert len(models.list_listings(status="sold", db_path=db_path)) == 1
        assert len(models.list_listings(db_path=db_path)) == 6


class TestBatchUpdateEdgeCases:
    def test_batch_update_single_id(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Solo", asking_price=10), db_path)
        count = models.batch_update_status([lid], "active", db_path)
        assert count == 1

    def test_batch_update_empty_list(self, db_path):
        count = models.batch_update_status([], "active", db_path)
        assert count == 0

    def test_batch_update_to_sold(self, db_path):
        ids = []
        for i in range(3):
            lid = models.create_listing(models.ListingCreate(title=f"I{i}", asking_price=10), db_path)
            ids.append(lid)
        count = models.batch_update_status(ids, "sold", db_path)
        assert count == 3
        for lid in ids:
            assert models.get_listing(lid, db_path).status == "sold"


class TestPhotosEdgeCases:
    def test_multiple_primary_photos(self, db_path):
        """Multiple photos marked as primary — should still work."""
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=10), db_path)
        models.add_photo(lid, "a.jpg", True, db_path)
        models.add_photo(lid, "b.jpg", True, db_path)
        photos = models.get_photos(lid, db_path)
        assert len(photos) == 2
        assert all(p.is_primary for p in photos)

    def test_no_photos(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=10), db_path)
        photos = models.get_photos(lid, db_path)
        assert photos == []

    def test_photos_for_nonexistent_listing(self, db_path):
        photos = models.get_photos(999, db_path)
        assert photos == []

    def test_many_photos(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=10), db_path)
        for i in range(10):
            models.add_photo(lid, f"photo_{i}.jpg", i == 0, db_path)
        photos = models.get_photos(lid, db_path)
        assert len(photos) == 10
        assert photos[0].is_primary is True


class TestOffersEdgeCases:
    def test_offer_with_all_optional_fields(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(
                listing_id=lid, buyer_name="Full Buyer", buyer_phone="202-555-1234",
                buyer_email="buyer@example.com", offer_amount=80.0,
                message="I really want this!",
            ),
            db_path,
        )
        offers = models.list_offers(listing_id=lid, db_path=db_path)
        assert len(offers) == 1
        assert offers[0].buyer_email == "buyer@example.com"
        assert offers[0].message == "I really want this!"

    def test_offer_minimal_fields(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(
                listing_id=lid, buyer_name="Min", buyer_phone="555",
                offer_amount=50.0,
            ),
            db_path,
        )
        offers = models.list_offers(listing_id=lid, db_path=db_path)
        assert offers[0].buyer_email is None
        assert offers[0].message is None

    def test_list_all_offers(self, db_path):
        lid1 = models.create_listing(models.ListingCreate(title="A", asking_price=100), db_path)
        lid2 = models.create_listing(models.ListingCreate(title="B", asking_price=200), db_path)
        models.create_offer(
            models.OfferCreate(listing_id=lid1, buyer_name="X", buyer_phone="1", offer_amount=50), db_path
        )
        models.create_offer(
            models.OfferCreate(listing_id=lid2, buyer_name="Y", buyer_phone="2", offer_amount=100), db_path
        )
        all_offers = models.list_offers(db_path=db_path)
        assert len(all_offers) == 2

    def test_update_offer_status_not_found(self, db_path):
        result = models.update_offer_status(999, "accepted", "Deal!", db_path)
        assert result is False

    def test_offer_default_status_is_pending(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="1", offer_amount=50), db_path
        )
        offers = models.list_offers(listing_id=lid, db_path=db_path)
        assert offers[0].status == "pending"


class TestForeignKeyEnforcement:
    def test_photo_fk_enforced(self, db_path):
        """Adding a photo for nonexistent listing should fail with FK enabled."""
        conn = get_connection(db_path)
        with pytest.raises(Exception):
            conn.execute(
                "INSERT INTO photos (listing_id, file_path, is_primary) VALUES (?, ?, ?)",
                (999, "ghost.jpg", 0),
            )
            conn.commit()
        conn.close()

    def test_offer_fk_enforced(self, db_path):
        """Adding an offer for nonexistent listing should fail with FK enabled."""
        conn = get_connection(db_path)
        with pytest.raises(Exception):
            conn.execute(
                "INSERT INTO offers (listing_id, buyer_name, buyer_phone, offer_amount) VALUES (?, ?, ?, ?)",
                (999, "Ghost", "555", 50.0),
            )
            conn.commit()
        conn.close()
