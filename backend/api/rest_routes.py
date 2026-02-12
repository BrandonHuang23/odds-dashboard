"""
REST API routes for the Odds Dashboard.

These endpoints serve metadata (sports, games, markets) to the Svelte frontend.
They proxy BoltOdds REST endpoints with caching to stay within rate limits.

The frontend calls these on page load and when the user changes selections,
BEFORE establishing a WebSocket connection for live odds.

EDUCATIONAL: REST vs WebSocket - When to Use Each
===================================================
REST is ideal for:
  - Request-response patterns (fetch a list, get details)
  - Data that changes infrequently (sports list, game schedule)
  - Cacheable responses

WebSocket is ideal for:
  - Continuous streaming data (live odds updates)
  - Server-initiated pushes (no need to poll)
  - Low-latency requirements
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/sports")
async def get_sports(request: Request):
    """
    Return available sports and sportsbooks.

    First tries the live state store (what we've actually seen from the WS feed),
    then falls back to the BoltOdds REST API for discovery.
    """
    store = request.app.state.store
    rest_client = request.app.state.rest_client

    # Try state store first (already populated from WS stream)
    live_sports = store.get_sports()
    if live_sports:
        # Also get sportsbooks from live data
        sportsbooks = sorted(store.active_sportsbooks)
        return {"sports": live_sports, "sportsbooks": sportsbooks}

    # Fall back to REST API
    try:
        info = await rest_client.get_info()
        return info
    except Exception as e:
        logger.error(f"Failed to fetch sports info: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch sports info from BoltOdds")


@router.get("/games/{sport}")
async def get_games(sport: str, request: Request):
    """
    Return available games for a sport.

    Primarily uses the live state store, which has real-time game data from
    the WebSocket feed. Falls back to REST API if needed.
    """
    store = request.app.state.store
    rest_client = request.app.state.rest_client

    # Get games from live state (most accurate - reflects what we're actually tracking)
    live_games = store.get_games_for_sport(sport)
    if live_games:
        return {"sport": sport, "games": list(live_games.values())}

    # Fall back to REST
    try:
        games = await rest_client.get_games(sport=sport)
        return {"sport": sport, "games": games}
    except Exception as e:
        logger.error(f"Failed to fetch games for {sport}: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch games for {sport}")


@router.get("/markets/{sport}")
async def get_markets(sport: str, request: Request, game_id: Optional[str] = None):
    """
    Return available market types for a sport, optionally filtered by game.

    If game_id is provided, returns markets that actually have odds data
    for that specific game. Otherwise returns all markets for the sport.
    """
    store = request.app.state.store
    rest_client = request.app.state.rest_client

    # If a specific game is requested, get markets from live state
    if game_id:
        markets = store.get_markets_for_game(game_id)
        if markets:
            return {"sport": sport, "game_id": game_id, "markets": markets}

    # Fall back to REST API for general market discovery
    try:
        markets = await rest_client.get_markets(sport=sport)
        return {"sport": sport, "markets": markets}
    except Exception as e:
        logger.error(f"Failed to fetch markets for {sport}: {e}")
        raise HTTPException(status_code=502, detail=f"Failed to fetch markets for {sport}")


@router.get("/status")
async def get_status(request: Request):
    """Return current system status - useful for debugging and health checks."""
    upstream = request.app.state.upstream
    store = request.app.state.store

    return {
        "upstream_connected": upstream.connected,
        "games_tracked": store.game_count,
        "sportsbooks_active": len(store.active_sportsbooks),
        "sports": store.get_sports(),
    }
