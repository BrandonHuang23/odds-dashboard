"""
BoltOdds REST API client.

Provides async wrappers for the three BoltOdds metadata endpoints:
  - /get_info    -> available sports and sportsbooks
  - /get_games   -> games for a given sport
  - /get_markets -> market types for a given sport

EDUCATIONAL: We use httpx (async) instead of requests (sync) because this
runs inside FastAPI, which is an async web framework. Using a sync HTTP
client would block the entire event loop during the request, preventing
the server from handling other connections.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

import httpx

from config import BOLTODDS_API_KEY, BOLTODDS_REST_BASE

logger = logging.getLogger(__name__)


class BoltOddsRestClient:
    """Async HTTP client for BoltOdds metadata endpoints with TTL caching."""

    def __init__(self, api_key: str = BOLTODDS_API_KEY):
        self._api_key = api_key
        self._base_url = BOLTODDS_REST_BASE
        self._client: Optional[httpx.AsyncClient] = None
        # Simple TTL cache: {cache_key: (data, expiry_timestamp)}
        self._cache: dict[str, tuple[Any, float]] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=15.0)
        return self._client

    def _cache_get(self, key: str) -> Any | None:
        """Return cached value if not expired, else None."""
        if key in self._cache:
            data, expiry = self._cache[key]
            if time.time() < expiry:
                return data
            del self._cache[key]
        return None

    def _cache_set(self, key: str, data: Any, ttl_seconds: float):
        """Store a value in cache with TTL."""
        self._cache[key] = (data, time.time() + ttl_seconds)

    async def get_info(self) -> dict:
        """
        Get available sports and sportsbooks from BoltOdds.

        Returns dict with 'sports' and 'sportsbooks' keys.
        Cached for 60 seconds (this data rarely changes).
        """
        cache_key = "info"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        client = await self._get_client()
        url = f"{self._base_url}/get_info?key={self._api_key}"
        logger.info("BoltOdds REST: GET /get_info")

        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        self._cache_set(cache_key, data, ttl_seconds=60)
        return data

    async def get_games(self, sport: str = None) -> list:
        """
        Get available games, optionally filtered by sport.

        Cached for 30 seconds (new games appear periodically).
        """
        cache_key = f"games:{sport or 'all'}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        client = await self._get_client()
        url = f"{self._base_url}/get_games?key={self._api_key}"
        if sport:
            url += f"&sports={sport}"

        logger.info(f"BoltOdds REST: GET /get_games?sports={sport}")

        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        self._cache_set(cache_key, data, ttl_seconds=30)
        return data

    async def get_markets(self, sport: str = None, sportsbooks: str = None) -> list:
        """
        Get available market types, optionally filtered by sport and sportsbook.

        Cached for 30 seconds.
        """
        cache_key = f"markets:{sport or 'all'}:{sportsbooks or 'all'}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        client = await self._get_client()
        url = f"{self._base_url}/get_markets?key={self._api_key}"
        if sport:
            url += f"&sports={sport}"
        if sportsbooks:
            url += f"&sportsbooks={sportsbooks}"

        logger.info(f"BoltOdds REST: GET /get_markets?sports={sport}")

        response = await client.get(url)
        response.raise_for_status()
        data = response.json()

        self._cache_set(cache_key, data, ttl_seconds=30)
        return data

    async def close(self):
        """Close the underlying HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
