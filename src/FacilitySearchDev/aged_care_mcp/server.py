"""Aged Care MCP Server"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from aged_care_mcp.repository import FacilityRepository


mcp = FastMCP(
    "aged-care-facilities",
    host="0.0.0.0",
    port=int(os.getenv("PORT", "8000")),
)

DEFAULT_DATA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "aged_care_facilities_state.jsonl"
)

DATA_PATH = Path(os.getenv("AGED_CARE_JSONL_PATH", DEFAULT_DATA_PATH))

repo = FacilityRepository(DATA_PATH)


@mcp.tool()
def search_facilities(
    query: str | None = None,
    suburb: str | None = None,
    postcode: str | None = None,
    state: str | None = "VIC",
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
    Search aged care facilities by name, address, suburb, postcode, state,
    star rating, and room-level constraints.

    Room-level filters return facilities that have at least one matching room.

    Args:
        query: Optional free-text search over facility name, address, suburb, and provider slug.
        suburb: Optional suburb filter.
        postcode: Optional postcode filter.
        state: Optional state filter. Defaults to VIC.
        limit: Maximum number of facilities to return. Clamped between 1 and 50.
        min_star_rating: Optional minimum star rating, for example 4.
        available_only: If true, only return facilities with at least one currently available room.
        min_rad: Optional minimum refundable accommodation deposit.
        max_rad: Optional maximum refundable accommodation deposit.
        min_dap: Optional minimum daily accommodation payment.
        max_dap: Optional maximum daily accommodation payment.
        exclude_shared_rooms: If true, only match non-shared/single-occupancy rooms.
    """
    limit = max(1, min(limit, 50))

    if min_star_rating is not None:
        min_star_rating = max(1, min(min_star_rating, 5))

    return repo.search_facilities(
        query=query,
        suburb=suburb,
        postcode=postcode,
        state=state,
        limit=limit,
        min_star_rating=min_star_rating,
        available_only=available_only,
        min_rad=min_rad,
        max_rad=max_rad,
        min_dap=min_dap,
        max_dap=max_dap,
        exclude_shared_rooms=exclude_shared_rooms,
    )


@mcp.tool()
def get_facility_details(facility_id: str) -> dict[str, Any]:
    """
    Get full details for one aged care facility by facility_id.

    Use this after search_facilities when the user wants contact details,
    address, website, map link, star rating, or source URLs.
    """
    facility = repo.get_facility_details(facility_id)

    if facility is None:
        return {
            "error": "facility_not_found",
            "facility_id": facility_id,
        }

    return facility


@mcp.tool()
def get_rooms_for_facility(facility_id: str) -> dict[str, Any]:
    """
    Get room and pricing information for one aged care facility by facility_id.

    Use this after search_facilities or get_facility_details when the user
    asks about available rooms, room types, RAD, DAP, size, occupancy, or costs.
    """
    facility = repo.get_facility_details(facility_id)

    if facility is None:
        return {
            "error": "facility_not_found",
            "facility_id": facility_id,
            "rooms": [],
        }

    return {
        "facility_id": facility_id,
        "facility_name": facility.get("facility_name"),
        "facility_address_full": facility.get("facility_address_full"),
        "rooms": repo.get_rooms_for_facility(facility_id),
    }


def main() -> None:
    """Start the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
