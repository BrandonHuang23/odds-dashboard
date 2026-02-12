"""
Upstream BoltOdds WebSocket client.

Maintains a persistent connection to BoltOdds, subscribes broadly to all
sports/sportsbooks/markets, and feeds updates into the StateStore.

EDUCATIONAL: The WebSocket Connection Lifecycle
================================================
A WebSocket connection goes through these phases:
  1. CONNECT  - TCP handshake + HTTP upgrade to WebSocket protocol
  2. AUTH     - BoltOdds sends an acknowledgment with your plan info
  3. SUBSCRIBE - We tell BoltOdds what data we want
  4. INITIAL BURST - Server dumps 100+ messages rapidly (accumulated state)
  5. STEADY STATE  - Server sends incremental updates as odds change
  6. CLOSE/RECONNECT - Connection drops, we reconnect and re-subscribe

This client handles all phases, including automatic reconnection with
exponential backoff. It runs as a background asyncio task within FastAPI.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING, Callable, Coroutine, Optional

from boltodds.state_store import StateStore
from boltodds.ws_utils import DEFAULT_BOLTODDS_WS_MAX_SIZE, parse_boltodds_ws_payload
from config import BOLTODDS_API_KEY, BOLTODDS_WS_URL

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    websockets = None
    ConnectionClosed = Exception

logger = logging.getLogger(__name__)


class BoltOddsUpstreamClient:
    """
    Persistent WebSocket client that connects to BoltOdds and feeds a StateStore.

    EDUCATIONAL: This is the SERVER-SIDE WebSocket client. Our FastAPI server
    acts as a client to BoltOdds (upstream) and as a server to browsers
    (downstream). This dual role is the "WebSocket proxy" pattern.
    """

    def __init__(
        self,
        api_key: str = BOLTODDS_API_KEY,
        state_store: StateStore = None,
        on_update: Optional[Callable[[list[str]], Coroutine]] = None,
    ):
        """
        Args:
            api_key: BoltOdds API key
            state_store: Shared state store to merge updates into
            on_update: Async callback called with list of changed game_ids
                       after each processed message batch
        """
        if websockets is None:
            raise ImportError("websockets package required: pip install websockets")

        self._api_key = api_key
        self._store = state_store or StateStore()
        self._on_update = on_update

        self._ws = None
        self._connected = False
        self._listen_task: Optional[asyncio.Task] = None
        self._running = False

        # Reconnection state
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def store(self) -> StateStore:
        return self._store

    async def connect(self):
        """
        Establish WebSocket connection and wait for acknowledgment.

        EDUCATIONAL: The connect phase involves:
          1. websockets.connect() - performs TCP + HTTP upgrade handshake
          2. Server sends an ack message with plan/quota info
          3. We're now ready to subscribe
        """
        url = f"{BOLTODDS_WS_URL}?key={self._api_key}"
        logger.info("Connecting to BoltOdds WebSocket...")

        self._ws = await websockets.connect(url, max_size=DEFAULT_BOLTODDS_WS_MAX_SIZE)
        self._connected = True

        # Wait for the initial ack from BoltOdds
        ack = await asyncio.wait_for(self._ws.recv(), timeout=10)
        logger.info(f"BoltOdds connected, ack received")

        # Reset reconnect delay on successful connection
        self._reconnect_delay = 1.0

    async def subscribe(
        self,
        sports: list[str] = None,
        sportsbooks: list[str] = None,
        markets: list[str] = None,
    ):
        """
        Subscribe to odds updates from BoltOdds.

        We subscribe broadly (no filters) so that any frontend client can view
        any sport/game/market without needing to re-subscribe upstream.

        EDUCATIONAL: The subscription message tells BoltOdds what data to stream.
        After subscribing, we'll receive an "initial burst" of 100+ messages
        containing the current state, followed by continuous incremental updates.
        """
        if not self._connected:
            raise RuntimeError("Not connected. Call connect() first.")

        subscription: dict = {"action": "subscribe", "filters": {}}
        if sports:
            subscription["filters"]["sports"] = sports
        if sportsbooks:
            subscription["filters"]["sportsbooks"] = sportsbooks
        if markets:
            subscription["filters"]["markets"] = markets

        await self._ws.send(json.dumps(subscription))
        logger.info(f"Subscribed to BoltOdds: {subscription['filters'] or 'all'}")

    async def connect_and_subscribe(self):
        """Convenience: connect, subscribe broadly, start listening."""
        await self.connect()
        # Subscribe to everything - let the frontend decide what to display
        await self.subscribe()
        await self.start_listening()

    async def start_listening(self):
        """Start the background listen loop as an asyncio task."""
        if self._listen_task is not None:
            return
        self._running = True
        self._listen_task = asyncio.create_task(self._listen_loop())
        logger.info("BoltOdds listen loop started")

    async def _listen_loop(self):
        """
        Background loop that processes incoming WebSocket messages.

        EDUCATIONAL: This is the core consumer pattern for WebSocket clients.
        `async for message in ws` iterates over incoming messages until the
        connection closes. Each message may contain one or more logical updates
        (due to batching), which we parse and merge into the state store.

        When the connection drops, we attempt reconnection with exponential
        backoff (1s, 2s, 4s, 8s... up to 60s max).
        """
        while self._running:
            try:
                if not self._connected or self._ws is None:
                    # No usable connection — skip straight to reconnect
                    raise Exception("No active upstream connection")

                async for raw_message in self._ws:
                    if not self._running:
                        break

                    all_changed_games: set[str] = set()

                    for msg in parse_boltodds_ws_payload(raw_message):
                        action = msg.get("action")

                        if action in ("initial_state", "line_update"):
                            changed = self._store.process_update(msg)
                            all_changed_games.update(changed)

                        elif action == "game_removed":
                            self._store.remove_game(msg)

                        elif action == "ping":
                            pass  # Keep-alive, no action needed

                        elif action == "error":
                            logger.warning(f"BoltOdds error: {msg}")

                    # Notify downstream subscribers about changes
                    if all_changed_games and self._on_update:
                        try:
                            await self._on_update(list(all_changed_games))
                        except Exception as e:
                            logger.error(f"Error in on_update callback: {e}")

            except ConnectionClosed as e:
                logger.warning(f"BoltOdds WebSocket closed: {e}")
                self._connected = False

            except Exception as e:
                logger.error(f"BoltOdds listen loop error: {e}")
                self._connected = False

            # Reconnect if we're still supposed to be running
            if self._running:
                logger.info(
                    f"Reconnecting to BoltOdds in {self._reconnect_delay:.1f}s..."
                )
                await asyncio.sleep(self._reconnect_delay)

                # Exponential backoff: 1s -> 2s -> 4s -> ... -> 60s max
                self._reconnect_delay = min(
                    self._reconnect_delay * 2, self._max_reconnect_delay
                )

                try:
                    await self.connect()
                    await self.subscribe()
                    logger.info("Reconnected to BoltOdds successfully")
                except Exception as e:
                    logger.error(f"Reconnection failed: {e}")

    async def stop_listening(self):
        """Stop the background listening task."""
        self._running = False
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

    async def close(self):
        """Close the WebSocket connection and stop listening."""
        await self.stop_listening()
        if self._ws:
            await self._ws.close()
            self._connected = False
        logger.info("BoltOdds upstream client closed")
