"""API keys management - stub for email tool compatibility."""

from mcp.server.fastmcp import Context


def get_api_key_for_context(ctx: Context, key_name: str = "api_key") -> str | None:
    """Get API key for context - not implemented."""
    return None


def set_api_key_for_context(ctx: Context, api_key: str, key_name: str = "api_key") -> None:
    """Set API key for context - not implemented."""
    raise NotImplementedError("API key storage is no longer supported - use database instead")


def clear_api_key_for_context(ctx: Context, key_name: str = "api_key") -> bool:
    """Clear API key for context - not implemented."""
    return False
