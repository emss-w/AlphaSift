from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
import time
import logging

import requests


class KrakenAPIError(RuntimeError):
    pass


@dataclass(frozen=True)
class KrakenClientConfig:
    base_url: str
    api_key: Optional[str]
    api_secret: Optional[str]
    timeout_seconds: int = 10
    max_retries: int = 3
    backoff_seconds: float = 0.5


class KrakenClient:
    def __init__(self, config: KrakenClientConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.log = logging.getLogger(self.__class__.__name__)

    def _request(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.config.base_url}{path}"
        last_exc: Exception | None = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                resp = self.session.get(
                    url,
                    params=params,
                    timeout=self.config.timeout_seconds,
                )
                if resp.status_code >= 500:
                    raise KrakenAPIError(f"Server error {resp.status_code}")
                resp.raise_for_status()
                data = resp.json()
                if data.get("error"):
                    raise KrakenAPIError(f"Kraken error: {data['error']}")
                return data
            except (requests.RequestException, ValueError, KrakenAPIError) as exc:
                last_exc = exc
                if attempt < self.config.max_retries:
                    time.sleep(self.config.backoff_seconds * attempt)
                    continue
                break
        raise KrakenAPIError(f"Request failed after retries: {last_exc}")

    def get_asset_pairs(self) -> Dict[str, Any]:
        return self._request("/0/public/AssetPairs", params={})

    def get_ohlc(
        self,
        pair: str,
        interval: int,
        since: Optional[int] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"pair": pair, "interval": interval}
        if since is not None:
            params["since"] = since
        return self._request("/0/public/OHLC", params=params)

    # Placeholder for future private endpoint signing
    def _sign_request(self, path: str, data: Dict[str, Any]) -> Dict[str, str]:
        raise NotImplementedError("Private endpoint signing not implemented yet.")
