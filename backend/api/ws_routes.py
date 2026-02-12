"""
WebSocket endpoint for frontend clients.

This is the DOWNSTREAM WebSocket - serving our Svelte frontend with
filtered, real-time odds data.

EDUCATIONAL: Snapshot + Delta Protocol
========================================
When a client subscribes, we send a full "snapshot" of current state,
then stream incremental "update" messages as odds change. This is the
standard pattern for real-time systems:

  1. Client connects to WS
  2. Server sends "connected" ack
  3. Client sends "subscribe" {sport, game_id, market}
  4. Server sends "snapshot" (all current odds for that game/market)
  5. Server streams "update" messages (only changes, as they happen)
  6. Client sends "unsubscribe" or disconnects

The frontend merges updates into its local state, just like the backend
merges BoltOdds updates into the StateStore. It's turtles all the way down.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/odds")
async def websocket_odds(websocket: WebSocket):
    """
    WebSocket endpoint for live odds streaming to the frontend.

    EDUCATIONAL: This function runs for the ENTIRE lifetime of a client
    connection. It's not a quick request/response like REST - it blocks
    in a loop, waiting for messages from the client, until disconnect.

    The backend acts as a PROXY:
      - UPSTREAM: One persistent connection to BoltOdds (wss://spro.agency)
      - DOWNSTREAM: One connection per browser tab (this endpoint)

    Benefits of this proxy approach:
      1. Only ONE upstream connection regardless of browser tab count
      2. API key stays on the server (never exposed to browser)
      3. We can transform/filter data per-client
      4. Custom protocol optimized for our dashboard UI
    """
    await websocket.accept()

    manager = websocket.app.state.connection_manager
    store = websocket.app.state.store
    upstream = websocket.app.state.upstream

    client_id = manager.add_client(websocket)

    # Send connection acknowledgment
    await websocket.send_json({
        "type": "connected",
        "server_time": datetime.now(timezone.utc).isoformat(),
    })

    try:
        while True:
            # Wait for messages from the frontend
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "subscribe":
                await _handle_subscribe(
                    client_id, data, manager, store, websocket
                )

            elif msg_type == "unsubscribe":
                manager.clear_subscription(client_id)

            elif msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "server_time": datetime.now(timezone.utc).isoformat(),
                })

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected normally")
    except Exception as e:
        logger.error(f"Client {client_id} error: {e}")
    finally:
        manager.remove_client(client_id)


async def _handle_subscribe(
    client_id: str,
    data: dict,
    manager,
    store,
    websocket: WebSocket,
):
    """
    Handle a subscribe message from the frontend.

    When the user selects a sport, game, and market, the frontend sends:
      {"type": "subscribe", "sport": "NHL", "game_id": "...", "market": "Total"}

    We respond with a full snapshot of current odds, then the connection
    manager will send incremental updates as they arrive from BoltOdds.
    """
    sport = data.get("sport", "")
    game_id = data.get("game_id", "")
    market = data.get("market")

    # Update this client's subscription in the connection manager
    manager.set_subscription(client_id, sport, game_id, market)

    # Send a full snapshot of current state for this game/market
    snapshot = store.get_snapshot(game_id, market=market)

    if snapshot:
        await websocket.send_json({
            "type": "snapshot",
            **snapshot,
        })
        logger.info(
            f"Sent snapshot to {client_id}: {game_id}/{market} "
            f"({len(snapshot.get('odds', {}))} sportsbooks)"
        )
    else:
        # No data yet for this game - send an empty snapshot
        await websocket.send_json({
            "type": "snapshot",
            "sport": sport,
            "game_id": game_id,
            "home_team": "",
            "away_team": "",
            "game_description": "",
            "market": market,
            "odds": {},
        })
        logger.info(f"Sent empty snapshot to {client_id}: {game_id}/{market} (no data yet)")

    # Also send current system status
    await websocket.send_json({
        "type": "status",
        "upstream_connected": True,
        "games_tracked": store.game_count,
        "sportsbooks_active": len(store.active_sportsbooks),
    })
