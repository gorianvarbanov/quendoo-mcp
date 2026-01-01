"""Quendoo MCP Server - Multi-Tenant with FastMCP JWTVerifier"""
import os
import sys
from uuid import UUID
from typing import Optional

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context

# Import FastMCP JWTVerifier
try:
    from fastmcp.server.auth.providers.jwt import JWTVerifier
    JWT_VERIFIER_AVAILABLE = True
    print("[INFO] FastMCP JWTVerifier available", file=sys.stderr, flush=True)
except ImportError:
    JWT_VERIFIER_AVAILABLE = False
    print("[WARNING] FastMCP JWTVerifier not available",
          file=sys.stderr, flush=True)

from tools import (
    AutomationClient,
    EmailClient,
    register_automation_tools,
    register_email_tools,
)
from tools.client import QuendooClient
from api_key_manager_v2 import mt_key_manager
from security.auth import auth_manager
from database.connection import get_db_session
from database.models import User, Tenant

load_dotenv()

# ========================================
# INITIALIZE JWT VERIFIER
# ========================================

auth_provider = None
if JWT_VERIFIER_AVAILABLE:
    # Get public key from auth manager
    from security.auth import auth_manager

    try:
        public_key_pem = auth_manager.get_public_key_pem()
        issuer = os.getenv("JWT_ISSUER", "https://quendoo-mcp-multitenant-851052272168.us-central1.run.app")
        base_url = os.getenv("BASE_URL", "https://quendoo-mcp-multitenant-851052272168.us-central1.run.app")

        auth_provider = JWTVerifier(
            public_key=public_key_pem,
            issuer=issuer,
            algorithm="RS256",
            base_url=base_url
        )

        print(f"[AUTH] ✓ JWTVerifier initialized", file=sys.stderr, flush=True)
        print(f"[AUTH] ✓ Issuer: {issuer}", file=sys.stderr, flush=True)
        print(f"[AUTH] ✓ Algorithm: RS256", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[ERROR] Failed to initialize JWTVerifier: {e}", file=sys.stderr, flush=True)
        auth_provider = None
else:
    print("[WARNING] Running without JWT authentication!", file=sys.stderr, flush=True)


# ========================================
# INITIALIZE FASTMCP SERVER
# ========================================

server = FastMCP(
    name="quendoo-pms-mcp-multitenant",
    instructions=(
        "Quendoo Property Management System - Multi-Tenant SaaS\n\n"
        "🔐 Authentication: JWT RS256 tokens issued by web portal\n"
        "All API keys are stored encrypted per tenant\n\n"
        "📋 AVAILABLE TOOLS:\n"
        "- Property Management: Properties, booking modules, availability\n"
        "- Booking Offers: Get pricing and availability\n"
        "- Bookings: Create, update, retrieve bookings\n"
        "- Email: Send HTML emails\n"
        "- Voice Calls: Automated calls with Bulgarian support\n\n"
        "💡 TIP: Each tenant has isolated data and API keys.\n"
        "🌐 Get your JWT token from: https://portal-851052272168.us-central1.run.app\n"
    ),
    auth=auth_provider,  # JWT authentication enabled!
)


# ========================================
# HELPER FUNCTIONS
# ========================================

def get_tenant_id_from_context(ctx: Context) -> UUID:
    """
    Extract tenant_id from authenticated context.

    FastMCP provides ctx.auth_claims after successful OAuth authentication.

    Args:
        ctx: MCP Context with auth_claims

    Returns:
        UUID of the tenant

    Raises:
        ValueError: If not authenticated or tenant not found
    """
    if not hasattr(ctx, 'auth_claims') or not ctx.auth_claims:
        raise ValueError(
            "Not authenticated. Please authenticate via OAuth flow."
        )

    tenant_id_str = ctx.auth_claims.get('tenant_id')
    if not tenant_id_str:
        raise ValueError("Tenant ID not found in authentication claims")

    return UUID(tenant_id_str)


def get_quendoo_client(ctx: Context) -> QuendooClient:
    """
    Create tenant-specific QuendooClient using encrypted API key from database.

    Args:
        ctx: MCP Context with auth_claims

    Returns:
        QuendooClient configured for the tenant

    Raises:
        ValueError: If authentication fails or API key not configured
    """
    tenant_id = get_tenant_id_from_context(ctx)

    # Retrieve encrypted API key from database
    quendoo_api_key = mt_key_manager.get_api_key(tenant_id, "QUENDOO_API_KEY")

    if not quendoo_api_key:
        raise ValueError(
            "QUENDOO_API_KEY not configured for your account. "
            "Please add it via the web portal at: "
            "https://portal-851052272168.us-central1.run.app/dashboard"
        )

    print(f"[DEBUG] Using API key for tenant: {tenant_id}", file=sys.stderr, flush=True)
    return QuendooClient(api_key=quendoo_api_key)


# ========================================
# PROPERTY TOOLS (TENANT-AWARE)
# ========================================

@server.tool()
def get_property_settings(
    ctx: Context,
    api_lng: str | None = None,
    names: str | None = None
) -> dict:
    """
    Get property settings including rooms, rates, services, meals, beds, booking modules.

    Args:
        ctx: Context (automatically provided)
        api_lng: Language code (e.g., 'en', 'bg'). Optional.
        names: Comma-separated list of setting names to retrieve. Optional.
    """
    print(f"[TOOL] get_property_settings called", file=sys.stderr, flush=True)
    client = get_quendoo_client(ctx)
    params = {"api_lng": api_lng, "names": names}
    return client.get("/Property/getPropertySettings", params=params)


@server.tool()
def get_rooms_details(
    ctx: Context,
    api_lng: str | None = None,
    room_id: int | None = None
) -> dict:
    """
    Get detailed information for rooms.

    Args:
        ctx: Context (automatically provided)
        api_lng: Language code for room details. Optional.
        room_id: Specific room ID to get details for. Optional (returns all rooms if omitted).
    """
    print(f"[TOOL] get_rooms_details called", file=sys.stderr, flush=True)
    client = get_quendoo_client(ctx)
    params = {"api_lng": api_lng, "room_id": room_id}
    return client.get("/Property/getRoomsDetails", params=params)


# ========================================
# AVAILABILITY TOOLS (TENANT-AWARE)
# ========================================

@server.tool(name="get_availability")
def quendoo_get_availability(
    ctx: Context,
    date_from: str,
    date_to: str,
    sysres: str
) -> dict:
    """
    Get availability for a date range and system (e.g., 'BOOKING', 'AIRBNB').

    Args:
        ctx: Context (automatically provided)
        date_from: Start date in YYYY-MM-DD format
        date_to: End date in YYYY-MM-DD format
        sysres: System/channel code (e.g., 'BOOKING', 'AIRBNB', 'EXPEDIA')
    """
    print(f"[TOOL] get_availability called", file=sys.stderr, flush=True)
    client = get_quendoo_client(ctx)
    params = {"date_from": date_from, "date_to": date_to, "sysres": sysres}
    return client.get("/Availability/getAvailability", params=params)


@server.tool()
def update_availability(
    ctx: Context,
    values: list[dict]
) -> dict:
    """
    Update availability values for rooms or external rooms.

    Args:
        ctx: Context (automatically provided)
        values: List of availability updates with structure:
            [{"date": "YYYY-MM-DD", "room_id": 123, "availability": 5, "sysres": "BOOKING"}, ...]
    """
    print(f"[TOOL] update_availability called", file=sys.stderr, flush=True)
    client = get_quendoo_client(ctx)
    payload = {"values": values}
    return client.post("/Availability/updateAvailability", json=payload)


# ========================================
# BOOKING TOOLS (TENANT-AWARE)
# ========================================

@server.tool()
def get_bookings(ctx: Context) -> dict:
    """
    List all bookings for the property.

    Args:
        ctx: Context (automatically provided)
    """
    print(f"[TOOL] get_bookings called", file=sys.stderr, flush=True)
    client = get_quendoo_client(ctx)
    return client.get("/Booking/getBookings")


@server.tool()
def get_booking_offers(
    ctx: Context,
    date_from: str,
    nights: int,
    bm_code: str | None = None,
    api_lng: str | None = None,
    guests: list[dict] | None = None,
    currency: str | None = None
) -> dict:
    """
    Fetch booking offers for a booking module code and stay dates.
    Auto-detects first active booking module if bm_code not provided.

    Args:
        ctx: Context (automatically provided)
        date_from: Check-in date in YYYY-MM-DD format
        nights: Number of nights
        bm_code: Booking module code. Optional (auto-detects if omitted).
        api_lng: Language code. Optional.
        guests: List of guest configurations. Optional.
            Example: [{"adults": 2, "children_by_ages": [5, 8]}]
        currency: Currency code (e.g., 'EUR', 'USD'). Optional.
    """
    print(f"[TOOL] get_booking_offers called", file=sys.stderr, flush=True)
    client = get_quendoo_client(ctx)

    # Auto-detect booking module if not provided
    if not bm_code:
        settings = client.get("/Property/getPropertySettings", params={"names": "booking_modules"})
        booking_modules = settings.get("data", {}).get("booking_modules", [])
        active_modules = [m for m in booking_modules if m.get("is_active")]
        if not active_modules:
            return {"error": "No active booking modules found. Please configure booking modules in Quendoo."}
        bm_code = active_modules[0]["code"]
        print(f"[DEBUG] Auto-detected booking module: {bm_code}", file=sys.stderr, flush=True)

    params = {
        "bm_code": bm_code,
        "date_from": date_from,
        "nights": nights,
        "api_lng": api_lng,
        "currency": currency
    }

    # Add guests if provided
    if guests:
        for i, guest_room in enumerate(guests):
            if "adults" in guest_room:
                params[f"guests[{i}][adults]"] = guest_room["adults"]
            if "children_by_ages" in guest_room:
                for j, age in enumerate(guest_room["children_by_ages"]):
                    params[f"guests[{i}][children_by_ages][{j}]"] = age

    return client.get("/Property/getBookingOffers", params=params)


@server.tool()
def ack_booking(
    ctx: Context,
    b_id: int,
    ack: int
) -> dict:
    """
    Acknowledge a booking (mark as confirmed).

    Args:
        ctx: Context (automatically provided)
        b_id: Booking ID
        ack: Acknowledgment status (1 = acknowledged, 0 = not acknowledged)
    """
    print(f"[TOOL] ack_booking called", file=sys.stderr, flush=True)
    client = get_quendoo_client(ctx)
    params = {"b_id": b_id, "ack": ack}
    return client.get("/Booking/ackBooking", params=params)


@server.tool()
def post_room_assignment(
    ctx: Context,
    b_id: int,
    assigned_rooms: list[dict]
) -> dict:
    """
    Assign physical rooms to a booking.

    Args:
        ctx: Context (automatically provided)
        b_id: Booking ID
        assigned_rooms: List of room assignments with structure:
            [{"br_id": 123, "room_id": 456}, ...]
            where br_id is booking room ID and room_id is physical room ID
    """
    print(f"[TOOL] post_room_assignment called", file=sys.stderr, flush=True)
    client = get_quendoo_client(ctx)
    payload = {"b_id": b_id, "assigned_rooms": assigned_rooms}
    return client.post("/Booking/postRoomAssignment", json=payload)


@server.tool()
def post_external_property_data(
    ctx: Context,
    sysres: str,
    external_property_id: str
) -> dict:
    """
    Map external property ID to Quendoo property.

    Args:
        ctx: Context (automatically provided)
        sysres: System/channel code (e.g., 'BOOKING', 'AIRBNB')
        external_property_id: External property ID from the channel
    """
    print(f"[TOOL] post_external_property_data called", file=sys.stderr, flush=True)
    client = get_quendoo_client(ctx)
    payload = {"sysres": sysres, "external_property_id": external_property_id}
    return client.post("/Property/postExternalPropertyData", json=payload)


# ========================================
# REGISTER AUTOMATION & EMAIL TOOLS
# ========================================

# Note: These tools use environment variables for API keys
# In future, these can also be made tenant-aware by storing keys in database

automation_bearer = os.getenv("QUENDOO_AUTOMATION_BEARER")
if automation_bearer:
    automation_client = AutomationClient(bearer_token=automation_bearer)
    register_automation_tools(server, automation_client)
    print("[INFO] Automation tools registered", file=sys.stderr, flush=True)
else:
    print("[WARNING] QUENDOO_AUTOMATION_BEARER not set, automation tools disabled", file=sys.stderr, flush=True)

email_api_key = os.getenv("EMAIL_API_KEY")
if email_api_key:
    email_client = EmailClient(api_key=email_api_key)
    register_email_tools(server, email_client)
    print("[INFO] Email tools registered", file=sys.stderr, flush=True)
else:
    print("[WARNING] EMAIL_API_KEY not set, email tools disabled", file=sys.stderr, flush=True)


# ========================================
# MAIN
# ========================================

if __name__ == "__main__":
    print("=" * 60, file=sys.stderr, flush=True)
    print("Quendoo MCP Server - Multi-Tenant with OAuth 2.1", file=sys.stderr, flush=True)
    print("=" * 60, file=sys.stderr, flush=True)

    if JWT_VERIFIER_AVAILABLE:
        print("✓ JWT authentication: ENABLED", file=sys.stderr, flush=True)
        print(f"✓ Base URL: {auth_provider.base_url if auth_provider else 'N/A'}", file=sys.stderr, flush=True)
    else:
        print("⚠ JWT authentication: DISABLED", file=sys.stderr, flush=True)

    transport = os.getenv("MCP_TRANSPORT", "sse").lower()
    port = int(os.getenv("PORT", "8080"))
    print(f"✓ Transport: {transport}", file=sys.stderr, flush=True)
    print(f"✓ Port: {port}", file=sys.stderr, flush=True)
    print("=" * 60, file=sys.stderr, flush=True)

    # FastMCP run with explicit port binding
    server.run(transport=transport, host="0.0.0.0", port=port)
