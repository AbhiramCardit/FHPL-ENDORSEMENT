"""HTTP client for TPA API."""

import httpx


class TPAClient:
    """Handles authenticated HTTP calls to the TPA's endorsement API."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def submit_endorsement(self, payload: dict) -> dict:
        """Submit a single endorsement to TPA API. Returns response dict."""
        raise NotImplementedError
