"""Quendoo MCP Server - Simple API Key Authentication"""
import os
import sys

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context

from tools import (
    AutomationClient,
    EmailClient,
    register_automation_tools,
    register_email_tools,
)
from tools.client import QuendooClient
from api_key_manager import get_api_key, set_api_key, cleanup_api_key, get_api_key_status

load_dotenv()

# ========================================
# SIMPLE SERVER - NO OAUTH
# ========================================

server = FastMCP(
    name="quendoo-pms-mcp",
    instructions=(
        "Quendoo Property Management System\n\n"
        "🔑 API Key Management (24h cache):\n"
        "- set_quendoo_api_key: Set your API key (cached for 24h)\n"
        "- get_quendoo_api_key_status: Check API key status and expiry\n"
        "- cleanup_quendoo_api_key: Remove cached API key\n\n"
        "📋 AVAILABLE TOOLS:\n"
        "- Property Management: Properties, booking modules, availability\n"
        "- Bookings: Create, update, retrieve bookings\n"
        "- Email: Send HTML emails\n"
        "- Voice Calls: Automated calls with Bulgarian support\n\n"
    ),
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8080")),
)

# ========================================
# GET QUENDOO CLIENT
# ========================================

def get_quendoo_client() -> QuendooClient:
    """
    Create QuendooClient using API key from cache or environment.
    Tries cache first (24h validity), falls back to environment variable.
    """
    # Try to get from cache (with 24h expiry)
    quendoo_api_key = get_api_key()

    if not quendoo_api_key:
        raise ValueError(
            "QUENDOO_API_KEY not set or expired. "
            "Use set_quendoo_api_key() tool to set it, or configure in .env file."
        )

    print(f"[DEBUG] Using Quendoo API key (first 10 chars): {quendoo_api_key[:10]}...", file=sys.stderr, flush=True)
    return QuendooClient(api_key=quendoo_api_key)


# ========================================
# PROPERTY TOOLS
# ========================================

@server.tool()
def get_property_settings(
    api_lng: str | None = None,
    names: str | None = None
) -> dict:
    """
    Get property settings including rooms, rates, services, meals, beds, booking modules, payment methods, and channel codes.

    Args:
        api_lng: Language code (e.g., 'en', 'bg'). Optional.
        names: Comma-separated list of setting names to retrieve. Optional.
    """
    print(f"[DEBUG TOOL] get_property_settings called", file=sys.stderr, flush=True)
    client = get_quendoo_client()
    params = {"api_lng": api_lng, "names": names}
    return client.get("/Property/getPropertySettings", params=params)


@server.tool()
def get_rooms_details(
    api_lng: str | None = None,
    room_id: int | None = None
) -> dict:
    """
    Get detailed information for rooms. Optionally filter by room_id and language.

    Args:
        api_lng: Language code for room details. Optional.
        room_id: Specific room ID to get details for. Optional (returns all rooms if omitted).
    """
    print(f"[DEBUG TOOL] get_rooms_details called", file=sys.stderr, flush=True)
    client = get_quendoo_client()
    params = {"api_lng": api_lng, "room_id": room_id}
    return client.get("/Property/getRoomsDetails", params=params)


# ========================================
# AVAILABILITY TOOLS
# ========================================

@server.tool(name="get_availability")
def quendoo_get_availability(
    date_from: str,
    date_to: str,
    sysres: str
) -> dict:
    """
    Get availability for a date range and system (qdo or ext).

    Args:
        date_from: Start date in YYYY-MM-DD format
        date_to: End date in YYYY-MM-DD format
        sysres: System reservation type ('qdo' for Quendoo or 'ext' for external)
    """
    print(f"[DEBUG TOOL] get_availability called: {date_from} to {date_to}, sysres={sysres}", file=sys.stderr, flush=True)
    client = get_quendoo_client()
    params = {"date_from": date_from, "date_to": date_to, "sysres": sysres}
    result = client.get("/Availability/getAvailability", params=params)
    print(f"[DEBUG AVAILABILITY] API returned: {result is not None}", file=sys.stderr, flush=True)
    return result


@server.tool()
def update_availability(
    values: list[dict]
) -> dict:
    """
    Update availability values for rooms or external rooms.

    Args:
        values: List of availability updates, each containing:
            - date: Date in YYYY-MM-DD format
            - room_id or ext_room_id: Room identifier
            - avail: Availability count (integer)
    """
    print(f"[DEBUG TOOL] update_availability called", file=sys.stderr, flush=True)
    client = get_quendoo_client()
    payload = {"values": values}
    return client.post("/Availability/updateAvailability", json=payload)


# ========================================
# BOOKING TOOLS
# ========================================

@server.tool()
def get_bookings() -> dict:
    """
    List all bookings for the property.
    """
    print(f"[DEBUG TOOL] get_bookings called", file=sys.stderr, flush=True)
    client = get_quendoo_client()
    return client.get("/Booking/getBookings")


@server.tool()
def get_booking_offers(
    bm_code: str,
    date_from: str,
    nights: int,
    api_lng: str | None = None,
    guests: list[dict] | None = None,
    currency: str | None = None
) -> dict:
    """
    Fetch booking offers for a booking module code and stay dates.

    Args:
        bm_code: Booking module code (e.g., 'BM001')
        date_from: Check-in date in YYYY-MM-DD format
        nights: Number of nights
        api_lng: Language code. Optional.
        guests: List of guest objects. Optional.
        currency: Currency code (e.g., 'EUR', 'USD'). Optional.
    """
    print(f"[DEBUG TOOL] get_booking_offers called", file=sys.stderr, flush=True)
    client = get_quendoo_client()
    params = {
        "bm_code": bm_code,
        "date_from": date_from,
        "nights": nights,
        "api_lng": api_lng,
        "currency": currency
    }
    payload = {"guests": guests} if guests else {}
    return client.post("/Booking/getBookingOffers", params=params, json=payload)


@server.tool()
def ack_booking(
    booking_id: int,
    revision_id: str
) -> dict:
    """
    Acknowledge a booking using booking_id and revision_id.

    Args:
        booking_id: Booking ID
        revision_id: Revision ID
    """
    print(f"[DEBUG TOOL] ack_booking called", file=sys.stderr, flush=True)
    client = get_quendoo_client()
    payload = {"booking_id": booking_id, "revision_id": revision_id}
    return client.post("/Booking/ackBooking", json=payload)


@server.tool()
def post_room_assignment(
    booking_id: int,
    revision_id: str
) -> dict:
    """
    Send room assignment for a booking.

    Args:
        booking_id: Booking ID
        revision_id: Revision ID
    """
    print(f"[DEBUG TOOL] post_room_assignment called", file=sys.stderr, flush=True)
    client = get_quendoo_client()
    payload = {"booking_id": booking_id, "revision_id": revision_id}
    return client.post("/Booking/postRoomAssignment", json=payload)


@server.tool()
def post_external_property_data(
    data: dict
) -> dict:
    """
    Send external property mapping data to Quendoo.

    Args:
        data: External property data object
    """
    print(f"[DEBUG TOOL] post_external_property_data called", file=sys.stderr, flush=True)
    client = get_quendoo_client()
    return client.post("/Booking/postExternalPropertyData", json=data)


# ========================================
# API KEY MANAGEMENT TOOLS
# ========================================

@server.tool()
def set_quendoo_api_key(api_key: str) -> dict:
    """
    Set your Quendoo API key. The key will be cached for 24 hours.

    Args:
        api_key: Your Quendoo API key (get it from Quendoo dashboard)

    Returns:
        Success status and expiry information
    """
    print(f"[DEBUG TOOL] set_quendoo_api_key called", file=sys.stderr, flush=True)
    result = set_api_key(api_key)
    # Reload environment to pick up new key
    load_dotenv(override=True)
    return result


@server.tool()
def get_quendoo_api_key_status() -> dict:
    """
    Check the status of your cached Quendoo API key.

    Returns:
        Information about cached API key: validity, expiry time, time remaining
    """
    print(f"[DEBUG TOOL] get_quendoo_api_key_status called", file=sys.stderr, flush=True)
    return get_api_key_status()


@server.tool()
def cleanup_quendoo_api_key() -> dict:
    """
    Remove cached Quendoo API key and clear it from configuration.
    Use this when you want to switch to a different API key or for security.

    Returns:
        Success status and files that were cleaned up
    """
    print(f"[DEBUG TOOL] cleanup_quendoo_api_key called", file=sys.stderr, flush=True)
    result = cleanup_api_key()
    # Reload environment
    load_dotenv(override=True)
    return result


# Register automation and email tools
automation_bearer = os.getenv("QUENDOO_AUTOMATION_BEARER")
automation_client = AutomationClient(bearer_token=automation_bearer)
email_client = EmailClient()

register_automation_tools(server, automation_client)
register_email_tools(server, email_client)

if __name__ == "__main__":
    print("Quendoo MCP server running (simple API key mode)", file=sys.stderr)
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    server.run(transport=transport)
