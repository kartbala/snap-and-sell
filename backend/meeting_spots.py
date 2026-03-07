"""Safe public meeting spots in DC for item exchanges."""
from __future__ import annotations
import random
from dataclasses import dataclass


@dataclass
class MeetingSpot:
    name: str
    address: str
    spot_type: str  # "police", "library", "metro", "public"
    neighborhood: str
    notes: str | None = None


# Curated list of safe, well-lit, public meeting spots in DC
DC_MEETING_SPOTS = [
    MeetingSpot(
        name="Metropolitan Police - First District",
        address="101 M St SW, Washington, DC 20024",
        spot_type="police",
        neighborhood="Southwest",
        notes="Lobby open 24/7. Designated safe exchange zone.",
    ),
    MeetingSpot(
        name="Metropolitan Police - Second District",
        address="3320 Idaho Ave NW, Washington, DC 20016",
        spot_type="police",
        neighborhood="Tenleytown",
        notes="Lobby open 24/7. Well-lit parking lot.",
    ),
    MeetingSpot(
        name="Metropolitan Police - Third District",
        address="1620 V St NW, Washington, DC 20009",
        spot_type="police",
        neighborhood="U Street",
        notes="Lobby open 24/7.",
    ),
    MeetingSpot(
        name="Metropolitan Police - Fourth District",
        address="6001 Georgia Ave NW, Washington, DC 20011",
        spot_type="police",
        neighborhood="Brightwood",
        notes="Lobby open 24/7. Large parking lot.",
    ),
    MeetingSpot(
        name="Metropolitan Police - Fifth District",
        address="1805 Bladensburg Rd NE, Washington, DC 20002",
        spot_type="police",
        neighborhood="Trinidad",
        notes="Lobby open 24/7.",
    ),
    MeetingSpot(
        name="Metropolitan Police - Sixth District",
        address="100 42nd St NE, Washington, DC 20019",
        spot_type="police",
        neighborhood="Deanwood",
        notes="Lobby open 24/7.",
    ),
    MeetingSpot(
        name="Metropolitan Police - Seventh District",
        address="2455 Alabama Ave SE, Washington, DC 20020",
        spot_type="police",
        neighborhood="Congress Heights",
        notes="Lobby open 24/7.",
    ),
    MeetingSpot(
        name="Martin Luther King Jr. Memorial Library",
        address="901 G St NW, Washington, DC 20001",
        spot_type="library",
        neighborhood="Downtown",
        notes="Main entrance lobby. Well-staffed during hours.",
    ),
    MeetingSpot(
        name="Union Station Main Hall",
        address="50 Massachusetts Ave NE, Washington, DC 20002",
        spot_type="public",
        neighborhood="Capitol Hill",
        notes="Inside main hall near information desk. Cameras and security present.",
    ),
    MeetingSpot(
        name="Gallery Place Metro Station",
        address="701 7th St NW, Washington, DC 20001",
        spot_type="metro",
        neighborhood="Chinatown",
        notes="Station entrance lobby. High foot traffic area.",
    ),
    MeetingSpot(
        name="Tenleytown-AU Metro Station",
        address="4501 Wisconsin Ave NW, Washington, DC 20016",
        spot_type="metro",
        neighborhood="Tenleytown",
        notes="Street-level entrance. Well-lit, busy area.",
    ),
    MeetingSpot(
        name="Columbia Heights Metro Station",
        address="3030 14th St NW, Washington, DC 20009",
        spot_type="metro",
        neighborhood="Columbia Heights",
        notes="Plaza entrance. Adjacent to Target, high visibility.",
    ),
    MeetingSpot(
        name="Starbucks - Dupont Circle",
        address="1501 Connecticut Ave NW, Washington, DC 20036",
        spot_type="public",
        neighborhood="Dupont Circle",
        notes="Inside or on patio. Busy, well-lit location.",
    ),
    MeetingSpot(
        name="Georgetown Library",
        address="3260 R St NW, Washington, DC 20007",
        spot_type="library",
        neighborhood="Georgetown",
        notes="Main entrance. Quiet, safe neighborhood.",
    ),
    MeetingSpot(
        name="Anacostia Library",
        address="1800 Good Hope Rd SE, Washington, DC 20020",
        spot_type="library",
        neighborhood="Anacostia",
        notes="Front entrance area.",
    ),
]


def get_all_spots() -> list[MeetingSpot]:
    """Return all curated meeting spots."""
    return DC_MEETING_SPOTS


def suggest_spot(neighborhood: str | None = None) -> MeetingSpot:
    """Suggest a random safe meeting spot, optionally near a neighborhood."""
    if neighborhood:
        lower = neighborhood.lower()
        nearby = [s for s in DC_MEETING_SPOTS if lower in s.neighborhood.lower()]
        if nearby:
            return random.choice(nearby)
    return random.choice(DC_MEETING_SPOTS)


def spot_to_dict(spot: MeetingSpot) -> dict:
    """Convert a MeetingSpot to a JSON-serializable dict."""
    return {
        "name": spot.name,
        "address": spot.address,
        "type": spot.spot_type,
        "neighborhood": spot.neighborhood,
        "notes": spot.notes,
    }
