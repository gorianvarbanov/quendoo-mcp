import os
from typing import Any

import httpx
from mcp.server.fastmcp import Context, FastMCP


EMAIL_SERVICE_URL = "https://us-central1-quednoo-chatgtp-mailing.cloudfunctions.net/send_quendoo_email"


class EmailClient:
    """HTTP client for sending emails via Quendoo email service."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("EMAIL_API_KEY")

    def _require_api_key(self) -> str:
        if not self.api_key:
            raise ValueError("EMAIL_API_KEY is not set. Add it to .env or pass it to EmailClient.")
        return self.api_key

    def send_email(self, to: str, subject: str, message: str, api_key: str | None = None) -> Any:
        """Send an email via the Quendoo email cloud function."""
        key = api_key or self._require_api_key()
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        payload = {
            "to": to,
            "subject": subject,
            "message": message,
        }

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(EMAIL_SERVICE_URL, json=payload, headers=headers)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Email request failed with status {exc.response.status_code}: {exc.response.text}"
            ) from exc


def register_email_tools(server: FastMCP, client: EmailClient) -> None:
    """Register email sending tools."""

    @server.tool(
        description="Send an email via Quendoo email service. Supports HTML content in the message body."
    )
    def send_quendoo_email(
        to: str,
        subject: str,
        message: str,
        ctx: Context,
    ) -> str:
        """
        Send an email through the Quendoo email service.

        Args:
            to: Recipient email address
            subject: Email subject line
            message: Email body (supports HTML)
            ctx: MCP context (automatically provided)

        Returns:
            Success message with details
        """
        # Use client's default API key from environment
        try:
            result = client.send_email(
                to=to,
                subject=subject,
                message=message,
            )
            return f"Email sent successfully to {to}. Details: {result.get('details', 'No details')}"
        except Exception as e:
            return f"Failed to send email: {str(e)}"
