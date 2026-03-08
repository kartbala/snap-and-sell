"""Tests for notification CRUD operations."""

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


class TestNotificationCreate:
    def test_create_notification(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        nid = models.create_notification(lid, oid, "new_offer", db_path)
        assert nid > 0

    def test_create_returns_incrementing_ids(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid1 = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="A", buyer_phone="1", offer_amount=50),
            db_path,
        )
        oid2 = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="B", buyer_phone="2", offer_amount=60),
            db_path,
        )
        nid1 = models.create_notification(lid, oid1, "new_offer", db_path)
        nid2 = models.create_notification(lid, oid2, "new_offer", db_path)
        assert nid2 > nid1


class TestNotificationList:
    def test_list_pending(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        models.create_notification(lid, oid, "new_offer", db_path)
        pending = models.list_notifications(sent=False, db_path=db_path)
        assert len(pending) == 1
        assert pending[0].sent is False

    def test_list_excludes_sent(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        nid = models.create_notification(lid, oid, "new_offer", db_path)
        models.mark_notification_sent(nid, db_path)
        pending = models.list_notifications(sent=False, db_path=db_path)
        assert len(pending) == 0

    def test_list_all(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        nid = models.create_notification(lid, oid, "new_offer", db_path)
        models.mark_notification_sent(nid, db_path)
        oid2 = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="Y", buyer_phone="666", offer_amount=90),
            db_path,
        )
        models.create_notification(lid, oid2, "new_offer", db_path)
        all_notifs = models.list_notifications(db_path=db_path)
        assert len(all_notifs) == 2

    def test_notification_has_listing_and_offer_info(self, db_path):
        lid = models.create_listing(
            models.ListingCreate(title="Widget", asking_price=100), db_path
        )
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="Alice", buyer_phone="202-555-1234", offer_amount=80),
            db_path,
        )
        models.create_notification(lid, oid, "new_offer", db_path)
        pending = models.list_notifications(sent=False, db_path=db_path)
        n = pending[0]
        assert n.listing_id == lid
        assert n.offer_id == oid
        assert n.type == "new_offer"


class TestNotificationMarkSent:
    def test_mark_sent(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        nid = models.create_notification(lid, oid, "new_offer", db_path)
        result = models.mark_notification_sent(nid, db_path)
        assert result is True

    def test_mark_sent_nonexistent(self, db_path):
        result = models.mark_notification_sent(999, db_path)
        assert result is False

    def test_mark_sent_changes_flag(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        nid = models.create_notification(lid, oid, "new_offer", db_path)
        models.mark_notification_sent(nid, db_path)
        sent = models.list_notifications(sent=True, db_path=db_path)
        assert len(sent) == 1
        assert sent[0].sent is True


class TestNotificationCascadeDelete:
    def test_delete_listing_deletes_notifications(self, db_path):
        lid = models.create_listing(models.ListingCreate(title="Item", asking_price=100), db_path)
        oid = models.create_offer(
            models.OfferCreate(listing_id=lid, buyer_name="X", buyer_phone="555", offer_amount=80),
            db_path,
        )
        models.create_notification(lid, oid, "new_offer", db_path)
        models.delete_listing(lid, db_path)
        all_notifs = models.list_notifications(db_path=db_path)
        assert len(all_notifs) == 0
