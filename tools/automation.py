import os
from typing import Any, Dict

import httpx
from mcp.server.fastmcp import FastMCP


DEFAULT_AUTOMATION_BASE_URL = "https://us-central1-quednoo-chatgtp-mailing.cloudfunctions.net"


class AutomationClient:
    """HTTP client for Quendoo Cloud Automation functions."""

    def __init__(self, base_url: str | None = None, bearer_token: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("QUENDOO_AUTOMATION_BASE_URL") or DEFAULT_AUTOMATION_BASE_URL).rstrip("/")
        self.bearer_token = bearer_token or os.getenv("QUENDOO_AUTOMATION_BEARER")

    def _headers(self, extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not self.bearer_token:
            raise ValueError("QUENDOO_AUTOMATION_BEARER is not set.")
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        if extra:
            headers.update(extra)
        return headers

    def post(self, path: str, json: Dict[str, Any]) -> Any:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(url, json=json, headers=self._headers())
                resp.raise_for_status()
                return resp.json() if resp.content else {"status": resp.status_code}
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Request failed with status {exc.response.status_code}: {exc.response.text}"
            ) from exc


def register_automation_tools(server: FastMCP, client: AutomationClient) -> None:
    """Register tools for Quendoo Cloud Automation."""

    @server.tool(description="Initiate a voice call with a spoken message.")
    def make_call(phone: str, message: str) -> Any:
        payload = {"phone": phone, "message": message}
        return client.post("/make_call", payload)
