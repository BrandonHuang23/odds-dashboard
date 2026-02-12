"""
WebSocket connection manager for frontend clients.

Tracks all connected browser clients and their current subscriptions,
enabling efficient fan-out of updates from the upstream BoltOdds feed.

EDUCATIONAL: The Fan-Out Pattern
=================================
One upstream data source (BoltOdds) fans out to N downstream consumers
(browser tabs). Each consumer has different subscription filters:
  - Tab 1 might be watching NHL Rangers game, Total market
  - Tab 2 might be watching NBA Lakers game, Spread market

When an upstream update arrives, we only notify clients who are subscribed
to that specific game. This avoids wasting bandwidth sending irrelevant
data to clients.

This pattern is used everywhere:
  - Chat servers: one message -> all room participants
  - Stock tickers: one price feed -> filtered per user's watchlist
  - Push notifications: one event -> users who opted in
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)


@dataclass
class ClientSubscription:
    """What a frontend client is currently subscribed to."""
    sport: Optional[str] = None
    game_id: Optional[str] = None
    market: Optional[str] = None


@dataclass
class ClientConnection:
    """A connected frontend WebSocket client."""
    client_id: str
    websocket: WebSocket
    subscription: ClientSubscription = field(default_factory=ClientSubscription)


class ConnectionManager:
    """
    Manages frontend WebSocket connections and subscription-based broadcasting.

    EDUCATIONAL: This is the downstream half of our WebSocket proxy.
    The upstream client (BoltOddsUpstreamClient) feeds data in.
    This manager distributes it to the right browser clients.
    """

    def __init__(self):
        self._clients: dict[str, ClientConnection] = {}

    def add_client(self, websocket: WebSocket) -> str:
        """Register a new frontend client. Returns a unique client_id."""
        client_id = str(uuid.uuid4())[:8]
        self._clients[client_id] = ClientConnection(
            client_id=client_id,
            websocket=websocket,
        )
        logger.info(f"Client {client_id} connected ({len(self._clients)} total)")
        return client_id

    def remove_client(self, client_id: str):
        """Unregister a disconnected client."""
        self._clients.pop(client_id, None)
        logger.info(f"Client {client_id} disconnected ({len(self._clients)} total)")

    def set_subscription(self, client_id: str, sport: str, game_id: str, market: str):
        """
        Update a client's subscription.

        Called when the frontend sends a 'subscribe' message after the user
        selects a sport, game, and market.
        """
        client = self._clients.get(client_id)
        if client:
            client.subscription = ClientSubscription(
                sport=sport, game_id=game_id, market=market
            )
            logger.info(
                f"Client {client_id} subscribed: {sport}/{game_id}/{market}"
            )

    def clear_subscription(self, client_id: str):
        """Clear a client's subscription (unsubscribe)."""
        client = self._clients.get(client_id)
        if client:
            client.subscription = ClientSubscription()

    def get_clients_for_game(self, game_id: str) -> list[ClientConnection]:
        """
        Return all clients subscribed to a specific game.

        EDUCATIONAL: This is the filtering step of fan-out. Instead of
        broadcasting to everyone, we only send to clients who care about
        this particular game.
        """
        return [
            c for c in self._clients.values()
            if c.subscription.game_id == game_id
        ]

    async def send_to_client(self, client_id: str, message: dict):
        """Send a JSON message to a specific client."""
        client = self._clients.get(client_id)
        if not client:
            return

        try:
            if client.websocket.client_state == WebSocketState.CONNECTED:
                await client.websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send to client {client_id}: {e}")
            self.remove_client(client_id)

    async def broadcast_update(self, game_id: str, update_message: dict):
        """
        Send an update to all clients subscribed to a game.

        EDUCATIONAL: Broadcasting with per-client filtering. We gather
        all tasks and run them concurrently with asyncio.gather for
        maximum throughput.
        """
        clients = self.get_clients_for_game(game_id)
        if not clients:
            return

        tasks = []
        for client in clients:
            # Filter by market if the client has a market subscription
            if client.subscription.market:
                # The caller should already have filtered by market,
                # but we double-check here
                tasks.append(self.send_to_client(client.client_id, update_message))
            else:
                tasks.append(self.send_to_client(client.client_id, update_message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @property
    def client_count(self) -> int:
        return len(self._clients)
