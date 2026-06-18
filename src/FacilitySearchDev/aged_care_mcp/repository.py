"""Repository module for loading and querying aged care facility and room data from a JSONL file."""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any


FACILITY_FIELDS = [
    "facility_id",
    "provider_slug",
    "facility_name",
    "overall_star_rating",
    "facility_summary",
    "facility_phone",
    "facility_email",
    "facility_website",
    "maps_url",
    "facility_address_full",
    "facility_suburb",
    "facility_postcode",
    "facility_state",
    "detail_url",
    "rooms_url",
    "source_results_url",
]

ROOM_FIELDS = [
    "room_index",
    "room_group",
    "availability",
    "room_name",
    "room_type",
    "size",
    "maximum_room_occupancy",
    "max_refundable_room_deposit",
    "max_daily_room_payment",
    "combination_payment_example",
    "max_daily_payment_or_rad",
    "source_url",
]



def _parse_star_rating(value: Any) -> int | None:
    """
    Converts strings like 'Rated 4 out of 5 stars' to 4.
    """
    if value is None:
        return None

    match = re.search(r"Rated\s+(\d+)\s+out\s+of\s+5", str(value), re.IGNORECASE)
    if not match:
        return None

    return int(match.group(1))


def _parse_money(value: Any) -> float | None:
    """
    Converts values like '$600,000' or '$130.85' to a float.

    Returns None when the value is missing or contains no numeric content.
    """
    if value is None:
        return None

    cleaned = re.sub(r"[^0-9.]", "", str(value))

    if not cleaned:
        return None

    return float(cleaned)


def _room_is_available(room: dict[str, Any]) -> bool:
    """
    Returns True when the room availability text contains 'currently available'.
    """
    return "currently available" in str(room.get("availability") or "").lower()


def _room_is_shared(room: dict[str, Any]) -> bool:
    """
    Heuristically determines whether a room is shared.

    A room is considered shared if:
    - any of room_group, room_name, room_type, or maximum_room_occupancy contains
      the word 'shared' (case-insensitive), or
    - maximum_room_occupancy is present and not equal to '1'.
    """
    searchable = " ".join(
        str(room.get(field) or "")
        for field in [
            "room_group",
            "room_name",
            "room_type",
            "maximum_room_occupancy",
        ]
    ).lower()

    if "shared" in searchable:
        return True

    occupancy = str(room.get("maximum_room_occupancy") or "").strip()
    return occupancy not in ("", "1")


class FacilityRepository:
    """
    Loads aged care facility and room data from a JSONL file and provides search and retrieval 
    methods.
    """
    def __init__(self, jsonl_path: str | Path):
        self.jsonl_path = Path(jsonl_path)
        self.facilities: dict[str, dict[str, Any]] = {}
        self.rooms_by_facility: dict[str, list[dict[str, Any]]] = {}
        self.load()

    def load(self) -> None:
        """
        Loads data from the JSONL file into memory. Expects each line to be a JSON object 
        containing both facility and room information. Facilities are indexed by facility_id, 
        and rooms are grouped by their associated facility_id.
        """
        if not self.jsonl_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.jsonl_path}")

        with self.jsonl_path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                row = json.loads(line)
                facility_id = row.get("facility_id")

                if not facility_id:
                    continue

                if facility_id not in self.facilities:
                    self.facilities[facility_id] = {
                        field: row.get(field) for field in FACILITY_FIELDS
                    }

                room = {
                    field: row.get(field) for field in ROOM_FIELDS
                }

                if room.get("room_name") or room.get("room_type"):
                    self.rooms_by_facility.setdefault(facility_id, []).append(room)

    def search_facilities(
        self,
        query: str | None = None,
        suburb: str | None = None,
        postcode: str | None = None,
        state: str | None = None,
        limit: int = 20,
        min_star_rating: int | None = None,
        available_only: bool = False,
        min_rad: float | None = None,
        max_rad: float | None = None,
        min_dap: float | None = None,
        max_dap: float | None = None,
        exclude_shared_rooms: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Search facilities using text/location filters and optional room-level filters.

        Text query matching is case-insensitive and checks facility_name,
        facility_address_full, facility_suburb, and provider_slug.

        When any room filter is active (available_only, max_rad, max_dap,
        exclude_shared_rooms), facilities are included only if at least one room
        matches those room filters.

        Returns compact facility summaries including:
        facility_id, facility_name, suburb/postcode/state/address, overall_star_rating,
        total room_count, and matching_room_count.
        """
        query_lc = query.lower().strip() if query else None
        suburb_lc = suburb.lower().strip() if suburb else None
        state_lc = state.lower().strip() if state else None
        postcode = postcode.strip() if postcode else None

        results: list[dict[str, Any]] = []

        room_filters_are_active = any(
            [
                available_only,
                min_rad is not None,
                max_rad is not None,
                min_dap is not None,
                max_dap is not None,
                exclude_shared_rooms,
            ]
        )

        for facility in self.facilities.values():
            if query_lc:
                searchable = " ".join(
                    str(facility.get(field) or "")
                    for field in [
                        "facility_name",
                        "facility_address_full",
                        "facility_suburb",
                        "provider_slug",
                    ]
                ).lower()

                if query_lc not in searchable:
                    continue

            if suburb_lc and suburb_lc not in str(facility.get("facility_suburb") or "").lower():
                continue

            if postcode and postcode != str(facility.get("facility_postcode") or ""):
                continue

            if state_lc and state_lc != str(facility.get("facility_state") or "").lower():
                continue

            if min_star_rating is not None:
                star_rating = _parse_star_rating(facility.get("overall_star_rating"))

                if star_rating is None or star_rating < min_star_rating:
                    continue

            facility_id = facility["facility_id"]
            rooms = self.rooms_by_facility.get(facility_id, [])

            matching_rooms = rooms

            if room_filters_are_active:
                matching_rooms = [
                    room
                    for room in rooms
                    if self._room_matches_filters(
                        room=room,
                        available_only=available_only,
                        min_rad=min_rad,
                        max_rad=max_rad,
                        min_dap=min_dap,
                        max_dap=max_dap,
                        exclude_shared_rooms=exclude_shared_rooms,
                    )
                ]

                if not matching_rooms:
                    continue

            results.append(
                {
                    "facility_id": facility_id,
                    "facility_name": facility.get("facility_name"),
                    "facility_suburb": facility.get("facility_suburb"),
                    "facility_postcode": facility.get("facility_postcode"),
                    "facility_state": facility.get("facility_state"),
                    "facility_address_full": facility.get("facility_address_full"),
                    "overall_star_rating": facility.get("overall_star_rating"),
                    "room_count": len(rooms),
                    "matching_room_count": len(matching_rooms),
                }
            )

            if len(results) >= limit:
                break

        return results


    def _room_matches_filters(
        self,
        room: dict[str, Any],
        available_only: bool = False,
        min_rad: float | None = None,
        max_rad: float | None = None,
        min_dap: float | None = None,
        max_dap: float | None = None,
        exclude_shared_rooms: bool = False,
    ) -> bool:
        """
        Returns True if a room satisfies all active room filter constraints.
        """
        if available_only and not _room_is_available(room):
            return False

        if exclude_shared_rooms and _room_is_shared(room):
            return False
        
        rad = _parse_money(room.get("max_refundable_room_deposit"))
        dap = _parse_money(room.get("max_daily_room_payment"))

        if min_rad is not None:
            if rad is None or rad < min_rad:
                return False

        if max_rad is not None:
            if rad is None or rad > max_rad:
                return False    

        if min_dap is not None:
            if dap is None or dap < min_dap:
                return False

        if max_dap is not None:
            if dap is None or dap > max_dap:
                return False

        return True

    def get_facility_details(self, facility_id: str) -> dict[str, Any] | None:
        """
        Get full details for one aged care facility by facility_id. Returns None if not found."""
        return self.facilities.get(facility_id)

    def get_rooms_for_facility(self, facility_id: str) -> list[dict[str, Any]]:
        """
        Get room and pricing information for one aged care facility by facility_id. Returns an empty
        list if no rooms are found or if the facility_id does not exist.
        """
        return self.rooms_by_facility.get(facility_id, [])
