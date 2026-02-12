"""
In-memory accumulative odds state store.

This is the central data structure for the dashboard. It receives raw BoltOdds
WebSocket messages and merges them into a complete, queryable picture of all
current odds across all sports, games, sportsbooks, and markets.

EDUCATIONAL: The Accumulative Update Pattern
=============================================
BoltOdds does NOT send snapshots. Each message contains a partial update -
odds for one sportsbook, one game, some outcomes. We must MERGE each update
into our existing state, never replace it. This is identical to how databases
handle WAL (Write-Ahead Log) replay, or how Redux reducers merge actions.

Key rules:
  1. If odds are present -> upsert (create or update) the outcome slot
  2. If odds are null/empty -> the market is suspended, REMOVE that slot
  3. Never discard the entire game state on a single update
  4. Track previous_odds before overwriting for movement detection
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Normalize sportsbook names that have aliases
BOOK_ALIAS = {
    "ps3838": "pinnacle",
    "betonline": "betonlineag",
}


@dataclass
class OutcomeState:
    """A single outcome from one sportsbook (e.g., 'Over 5.5' from DraftKings)."""
    odds: str                           # American odds as string ("-110", "+150")
    outcome_name: str                   # Market name ("Total", "Spread", "Moneyline")
    outcome_line: Optional[str]         # Line value ("5.5", "-3.5") or None
    outcome_over_under: Optional[str]   # "O", "U", or None
    outcome_target: Optional[str]       # Team name for spread/ML, or None
    timestamp: str
    previous_odds: Optional[str] = None # For movement detection on the frontend


@dataclass
class GameState:
    """All odds for one game across all sportsbooks and markets."""
    sport: str
    home_team: str
    away_team: str
    game_description: str
    # Nested structure: sportsbook -> outcome_key -> OutcomeState
    odds: dict[str, dict[str, OutcomeState]] = field(default_factory=dict)
    last_update: str = ""


class StateStore:
    """
    Thread-safe (asyncio-safe) accumulative state store for all odds data.

    The store is organized by game_id, where each game contains odds from
    all sportsbooks. This allows efficient querying by sport, game, and market.
    """

    def __init__(self):
        self._games: dict[str, GameState] = {}
        self._lock = asyncio.Lock()

    def process_update(self, message: dict) -> list[str]:
        """
        Merge a line_update or initial_state message into accumulated state.

        Returns a list of game_ids that were changed (for notifying subscribers).

        EDUCATIONAL: This is the core merge function. Every WebSocket message
        passes through here. The logic must handle:
          - Creating new games on first sight
          - Adding new sportsbooks to existing games
          - Updating existing outcomes (with previous_odds tracking)
          - Removing suspended outcomes (null/empty odds)
        """
        data = message.get("data", {})
        timestamp = message.get("timestamp", datetime.now(timezone.utc).isoformat())

        sport = data.get("sport", "")
        sportsbook = data.get("sportsbook", "")
        home_team = data.get("home_team", "")
        away_team = data.get("away_team", "")
        game_desc = data.get("game", "")
        outcomes = data.get("outcomes", {})

        if not (home_team and away_team):
            return []

        # Normalize sportsbook name
        sportsbook = BOOK_ALIAS.get(sportsbook, sportsbook)

        # Build canonical game ID from team names (BoltOdds universal_game_id is unreliable)
        game_id = f"{away_team}@{home_team}".lower().replace(" ", "_")

        # Create game state if first time seeing this game
        if game_id not in self._games:
            self._games[game_id] = GameState(
                sport=sport,
                home_team=home_team,
                away_team=away_team,
                game_description=game_desc,
                last_update=timestamp,
            )

        game_state = self._games[game_id]
        game_state.last_update = timestamp

        # Ensure sportsbook dict exists
        if sportsbook not in game_state.odds:
            game_state.odds[sportsbook] = {}

        changed = False

        for outcome_key, outcome_data in outcomes.items():
            if not isinstance(outcome_data, dict):
                continue

            outcome_name = outcome_data.get("outcome_name", "")
            odds_str = outcome_data.get("odds")
            line_val = outcome_data.get("outcome_line")
            over_under_raw = outcome_data.get("outcome_over_under")
            outcome_target = outcome_data.get("outcome_target")

            # Parse over/under and line from potentially embedded format ("O 5.5")
            over_under = None
            line = None

            if over_under_raw and ' ' in str(over_under_raw):
                parts = str(over_under_raw).split(' ', 1)
                over_under = parts[0].upper()[:1] if parts[0] else None
                try:
                    line = str(float(parts[1]))
                except (ValueError, IndexError):
                    pass

            if over_under is None and over_under_raw:
                over_under = str(over_under_raw).upper()[:1]
                if over_under not in ('O', 'U'):
                    over_under = str(over_under_raw)

            if line is None and line_val is not None:
                try:
                    line = str(float(line_val))
                except (ValueError, TypeError):
                    line = str(line_val) if line_val else None

            # Build a unique key for this outcome within the sportsbook
            # This handles different market types naturally
            store_key = outcome_key

            # Check if odds are missing/null (market suspended)
            odds_missing = odds_str is None or (isinstance(odds_str, str) and not odds_str.strip())

            if odds_missing:
                # Remove suspended outcome
                if store_key in game_state.odds[sportsbook]:
                    del game_state.odds[sportsbook][store_key]
                    changed = True
                continue

            # Format odds as string
            if isinstance(odds_str, (int, float)):
                odds_str = str(int(odds_str))
            else:
                odds_str = str(odds_str).strip()

            # Track previous odds for movement detection
            previous_odds = None
            if store_key in game_state.odds[sportsbook]:
                existing = game_state.odds[sportsbook][store_key]
                if existing.odds != odds_str:
                    previous_odds = existing.odds

            game_state.odds[sportsbook][store_key] = OutcomeState(
                odds=odds_str,
                outcome_name=outcome_name,
                outcome_line=line,
                outcome_over_under=over_under if over_under in ('O', 'U') else None,
                outcome_target=outcome_target,
                timestamp=timestamp,
                previous_odds=previous_odds,
            )
            changed = True

        return [game_id] if changed else []

    def remove_game(self, message: dict):
        """Handle a game_removed message by removing the game from state."""
        data = message.get("data", {})
        home_team = data.get("home_team", "")
        away_team = data.get("away_team", "")
        if home_team and away_team:
            game_id = f"{away_team}@{home_team}".lower().replace(" ", "_")
            self._games.pop(game_id, None)

    def get_sports(self) -> list[str]:
        """Return list of sports currently in state."""
        sports = set()
        for game in self._games.values():
            sports.add(game.sport)
        return sorted(sports)

    def get_games_for_sport(self, sport: str) -> dict[str, dict]:
        """Return summary of all games for a sport."""
        result = {}
        for game_id, game_state in self._games.items():
            if game_state.sport.upper() == sport.upper():
                result[game_id] = {
                    "game_id": game_id,
                    "home_team": game_state.home_team,
                    "away_team": game_state.away_team,
                    "sport": game_state.sport,
                    "game_description": game_state.game_description,
                    "sportsbook_count": len(game_state.odds),
                    "last_update": game_state.last_update,
                }
        return result

    def get_markets_for_game(self, game_id: str) -> list[str]:
        """Return distinct market types available for a specific game."""
        game = self._games.get(game_id)
        if not game:
            return []
        markets = set()
        for book_outcomes in game.odds.values():
            for outcome in book_outcomes.values():
                if outcome.outcome_name:
                    markets.add(outcome.outcome_name)
        return sorted(markets)

    def get_snapshot(self, game_id: str, market: str = None) -> dict | None:
        """
        Build a complete snapshot for a game, optionally filtered by market.

        Returns the data in the frontend-friendly protocol format:
        {
            "sport": "NHL",
            "game_id": "...",
            "home_team": "...",
            "away_team": "...",
            "game_description": "...",
            "market": "Total",
            "odds": {
                "draftkings": {
                    "outcome_key": { odds, outcome_name, outcome_line, ... }
                },
                ...
            }
        }
        """
        game = self._games.get(game_id)
        if not game:
            return None

        odds_data: dict[str, dict[str, dict]] = {}

        for sportsbook, outcomes in game.odds.items():
            filtered_outcomes = {}
            for key, outcome in outcomes.items():
                if market and outcome.outcome_name != market:
                    continue
                filtered_outcomes[key] = {
                    "odds": outcome.odds,
                    "outcome_name": outcome.outcome_name,
                    "outcome_line": outcome.outcome_line,
                    "outcome_over_under": outcome.outcome_over_under,
                    "outcome_target": outcome.outcome_target,
                    "timestamp": outcome.timestamp,
                }
            if filtered_outcomes:
                odds_data[sportsbook] = filtered_outcomes

        return {
            "sport": game.sport,
            "game_id": game_id,
            "home_team": game.home_team,
            "away_team": game.away_team,
            "game_description": game.game_description,
            "market": market,
            "odds": odds_data,
        }

    def get_update_for_subscribers(
        self, game_id: str, sportsbook: str, market: str = None
    ) -> dict | None:
        """
        Build an incremental update message for a specific game + sportsbook,
        optionally filtered by market. Used to send deltas to frontend clients.
        """
        game = self._games.get(game_id)
        if not game:
            return None

        book_outcomes = game.odds.get(sportsbook, {})
        filtered = {}

        for key, outcome in book_outcomes.items():
            if market and outcome.outcome_name != market:
                continue
            filtered[key] = {
                "odds": outcome.odds,
                "outcome_name": outcome.outcome_name,
                "outcome_line": outcome.outcome_line,
                "outcome_over_under": outcome.outcome_over_under,
                "outcome_target": outcome.outcome_target,
                "previous_odds": outcome.previous_odds,
                "timestamp": outcome.timestamp,
            }

        if not filtered:
            return None

        return {
            "game_id": game_id,
            "sportsbook": sportsbook,
            "outcomes": filtered,
        }

    @property
    def game_count(self) -> int:
        return len(self._games)

    @property
    def active_sportsbooks(self) -> set[str]:
        books = set()
        for game in self._games.values():
            books.update(game.odds.keys())
        return books
