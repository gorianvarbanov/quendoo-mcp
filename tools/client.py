import os
from typing import Any, Dict

import httpx


DEFAULT_BASE_URL = "https://www.platform.quendoo.com/api/pms/v1/"


class QuendooClient:
    """Minimal HTTP client for the Quendoo PMS API."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None, api_lng: str | None = None) -> None:
        self.api_key = api_key or os.getenv("QUENDOO_API_KEY")
        self.base_url = (base_url or os.getenv("QUENDOO_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.default_lang = api_lng

    def _require_api_key(self) -> str:
        if not self.api_key:
            raise ValueError("QUENDOO_API_KEY is not set. Add it to .env or pass it to QuendooClient.")
        return self.api_key

    def _params(
        self, extra: Dict[str, Any] | None = None, api_key: str | None = None
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"api_key": api_key or self._require_api_key()}
        if self.default_lang:
            params["api_lng"] = self.default_lang
        if extra:
            params.update({k: v for k, v in extra.items() if v is not None})
        return params

    def get(self, path: str, params: Dict[str, Any] | None = None, api_key: str | None = None) -> Any:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url, params=self._params(params, api_key=api_key))
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Request failed with status {exc.response.status_code}: {exc.response.text}"
            ) from exc

    def post(
        self,
        path: str,
        json: Any | None = None,
        params: Dict[str, Any] | None = None,
        api_key: str | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=30) as client:
                resp = client.post(url, params=self._params(params, api_key=api_key), json=json or {})
                resp.raise_for_status()
                return resp.json() if resp.content else {"status": resp.status_code}
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"Request failed with status {exc.response.status_code}: {exc.response.text}"
            ) from exc
