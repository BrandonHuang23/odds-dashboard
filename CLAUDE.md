# CLAUDE.md

## Project Overview

Real-time sports odds comparison dashboard. Aggregates odds from multiple sportsbooks via the BoltOdds API and displays them in a live-updating grid. Uses a WebSocket proxy pattern: the backend maintains a single upstream connection to BoltOdds and fans out filtered data to multiple browser clients.

## Tech Stack

- **Backend**: Python 3.10+ / FastAPI / uvicorn / websockets / httpx
- **Frontend**: TypeScript / Svelte 5 / SvelteKit 2 / Vite 5
- **Deployment**: SvelteKit adapter-static (SPA mode)

## Project Structure

```
backend/           # FastAPI server
  main.py          # App entry point with lifespan management
  config.py        # Environment config (reads .env)
  api/             # REST and WebSocket route handlers
  boltodds/        # Upstream BoltOdds integration (ws_client, rest_client, state_store)
  services/        # Connection manager for downstream clients

frontend/          # SvelteKit SPA
  src/routes/      # Pages and layouts
  src/lib/
    components/    # Svelte components (OddsGrid, OddsCell, selectors, etc.)
    stores/        # Svelte stores (odds, selections, connection status)
    websocket/     # WS client and protocol types
    api/           # REST client for metadata
```

## Development Commands

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Requires a `.env` file in `backend/` with `BOLTODDS_API_KEY=<key>`.

### Frontend

```bash
cd frontend
npm install
npm run dev        # Dev server at http://localhost:5173
npm run build      # Production build
npm run preview    # Preview production build
npm run check      # Type-check with svelte-check
```

The Vite dev server proxies `/api/*` and `/ws/*` to `http://localhost:8000`.

## Key Architecture Patterns

- **WebSocket proxy**: Backend keeps one upstream BoltOdds connection; broadcasts filtered updates to browser clients. API key stays server-side.
- **Accumulative state store** (`state_store.py`): Merges partial updates, never replaces full state. Tracks `previous_odds` for movement detection.
- **Snapshot + delta protocol**: Initial full snapshot on subscribe, then incremental updates.
- **Reactive stores** (frontend): Svelte writable/derived stores auto-update the UI. Derived stores compute odds rows and best-price highlighting.
- **Exponential backoff reconnection**: Both backend (upstream) and frontend (downstream) implement this.

## Code Conventions

- Full type annotations in Python; strict TypeScript in frontend
- Async/await throughout the backend (FastAPI async endpoints, asyncio tasks)
- Svelte 5 component syntax with reactive `$:` declarations
- Dark theme via CSS custom properties
- Educational-style docstrings and comments explaining design decisions

## Common Tasks

- **Add a new sport/market**: Update the BoltOdds subscription parameters and add any new UI options in the selector components.
- **Add a new sportsbook column**: The OddsGrid dynamically renders columns based on data received; no hardcoded sportsbook list.
- **Modify odds display**: `OddsCell.svelte` handles individual cell rendering including movement indicators.

## No Tests

There is currently no test suite. If adding tests, use **pytest** for the backend and **vitest** for the frontend.
