"""Tests for meeting spots module."""

import pytest
from backend.meeting_spots import (
    MeetingSpot, DC_MEETING_SPOTS, get_all_spots,
    suggest_spot, spot_to_dict,
)


class TestMeetingSpotData:
    def test_spots_list_not_empty(self):
        assert len(DC_MEETING_SPOTS) > 0

    def test_all_spots_have_required_fields(self):
        for spot in DC_MEETING_SPOTS:
            assert spot.name
            assert spot.address
            assert spot.spot_type in ("police", "library", "metro", "public")
            assert spot.neighborhood

    def test_at_least_one_police_station(self):
        police = [s for s in DC_MEETING_SPOTS if s.spot_type == "police"]
        assert len(police) >= 1

    def test_at_least_one_library(self):
        libraries = [s for s in DC_MEETING_SPOTS if s.spot_type == "library"]
        assert len(libraries) >= 1

    def test_at_least_one_metro(self):
        metros = [s for s in DC_MEETING_SPOTS if s.spot_type == "metro"]
        assert len(metros) >= 1

    def test_unique_names(self):
        names = [s.name for s in DC_MEETING_SPOTS]
        assert len(names) == len(set(names))

    def test_all_dc_addresses(self):
        for spot in DC_MEETING_SPOTS:
            assert "Washington" in spot.address or "DC" in spot.address


class TestGetAllSpots:
    def test_returns_all(self):
        spots = get_all_spots()
        assert len(spots) == len(DC_MEETING_SPOTS)

    def test_returns_meetingspot_instances(self):
        spots = get_all_spots()
        for s in spots:
            assert isinstance(s, MeetingSpot)


class TestSuggestSpot:
    def test_returns_a_spot(self):
        spot = suggest_spot()
        assert isinstance(spot, MeetingSpot)
        assert spot in DC_MEETING_SPOTS

    def test_neighborhood_filter(self):
        spot = suggest_spot(neighborhood="Tenleytown")
        assert "Tenleytown" in spot.neighborhood

    def test_neighborhood_case_insensitive(self):
        spot = suggest_spot(neighborhood="tenleytown")
        assert "Tenleytown" in spot.neighborhood

    def test_unknown_neighborhood_returns_any(self):
        spot = suggest_spot(neighborhood="Narnia")
        assert isinstance(spot, MeetingSpot)

    def test_none_neighborhood_returns_any(self):
        spot = suggest_spot(neighborhood=None)
        assert isinstance(spot, MeetingSpot)


class TestSpotToDict:
    def test_all_keys_present(self):
        spot = DC_MEETING_SPOTS[0]
        d = spot_to_dict(spot)
        assert "name" in d
        assert "address" in d
        assert "type" in d
        assert "neighborhood" in d
        assert "notes" in d

    def test_values_match(self):
        spot = MeetingSpot(
            name="Test", address="123 Main St", spot_type="public",
            neighborhood="TestVille", notes="A note",
        )
        d = spot_to_dict(spot)
        assert d["name"] == "Test"
        assert d["address"] == "123 Main St"
        assert d["type"] == "public"
        assert d["neighborhood"] == "TestVille"
        assert d["notes"] == "A note"

    def test_none_notes(self):
        spot = MeetingSpot(
            name="T", address="A", spot_type="police", neighborhood="N",
        )
        d = spot_to_dict(spot)
        assert d["notes"] is None
