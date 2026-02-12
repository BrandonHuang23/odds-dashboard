"""
Odds Dashboard - FastAPI Backend Entry Point

This is the main application file that wires together all components:
  - BoltOdds upstream WebSocket client (connects to BoltOdds)
  - StateStore (accumulates all odds in memory)
  - ConnectionManager (manages frontend WebSocket clients)
  - REST routes (serve metadata: sports, games, markets)
  - WebSocket route (stream live odds to frontend)

EDUCATIONAL: FastAPI Lifespan Events
======================================
Modern FastAPI uses a "lifespan" context manager (not the deprecated
@app.on_event decorators) to manage startup and shutdown logic.

On STARTUP:
  1. Create the StateStore
  2. Create the ConnectionManager
  3. Connect the upstream BoltOdds WebSocket client
  4. Start listening for upstream updates in a background task

On SHUTDOWN:
  1. Stop listening for upstream updates
  2. Close the BoltOdds connection
  3. Close the REST HTTP client

This ensures long-lived resources (WebSocket connections, HTTP clients)
are properly created and cleaned up with the server lifecycle.

Run with:
    cd backend
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.rest_routes import router as rest_router
from api.ws_routes import router as ws_router
from boltodds.rest_client import BoltOddsRestClient
from boltodds.state_store import StateStore
from boltodds.ws_client import BoltOddsUpstreamClient
from services.connection_manager import ConnectionManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle - startup and shutdown.

    EDUCATIONAL: The lifespan context manager replaces the old
    @app.on_event("startup") / @app.on_event("shutdown") pattern.
    Everything before `yield` runs on startup, everything after runs
    on shutdown. Resources created here live for the entire server lifetime.
    """
    # === STARTUP ===
    logger.info("Starting Odds Dashboard backend...")

    # Create shared components
    store = StateStore()
    connection_manager = ConnectionManager()
    rest_client = BoltOddsRestClient()

    # Create the upstream BoltOdds client with a callback that broadcasts
    # updates to subscribed frontend clients
    async def on_upstream_update(changed_game_ids: list[str]):
        """
        Called whenever the upstream BoltOdds feed updates odds for games.

        EDUCATIONAL: This callback bridges upstream and downstream.
        When BoltOdds sends us new odds -> we update the store -> then
        we notify all frontend clients watching those games.
        """
        for game_id in changed_game_ids:
            clients = connection_manager.get_clients_for_game(game_id)
            for client in clients:
                market = client.subscription.market
                # Get the filtered update for this client's market
                snapshot = store.get_snapshot(game_id, market=market)
                if snapshot:
                    await connection_manager.send_to_client(
                        client.client_id,
                        {"type": "update", **snapshot},
                    )

    upstream = BoltOddsUpstreamClient(
        state_store=store,
        on_update=on_upstream_update,
    )

    # Store references on app.state so routes can access them
    app.state.store = store
    app.state.connection_manager = connection_manager
    app.state.rest_client = rest_client
    app.state.upstream = upstream

    # Connect to BoltOdds and start listening
    try:
        await upstream.connect_and_subscribe()
        logger.info("BoltOdds upstream connection established")
    except Exception as e:
        logger.error(f"Failed to connect to BoltOdds: {e}")
        logger.info("Server will start anyway - upstream will retry in background")

    yield

    # === SHUTDOWN ===
    logger.info("Shutting down Odds Dashboard backend...")
    await upstream.close()
    await rest_client.close()
    logger.info("Shutdown complete")


# Create the FastAPI application
app = FastAPI(
    title="Odds Dashboard",
    description="Real-time sports odds comparison dashboard",
    lifespan=lifespan,
)

# CORS middleware - allow the Svelte dev server to make requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:4173",   # Vite preview
        "http://localhost:3000",   # Alternative port
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(rest_router)
app.include_router(ws_router)
