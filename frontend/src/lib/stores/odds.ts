/**
 * Odds data store.
 *
 * Holds the current odds snapshot received from the backend WebSocket.
 * Updated on both 'snapshot' (full replace) and 'update' (merge) messages.
 *
 * EDUCATIONAL: Reactive Data Flow from WebSocket
 * ================================================
 * The data flows through these stages:
 *   1. Backend WS sends 'snapshot' or 'update' message
 *   2. client.ts onMessage callback fires
 *   3. This store gets updated via oddsData.set() or oddsData.update()
 *   4. Svelte detects the store change
 *   5. All components using $oddsData automatically re-render
 *
 * No polling. No manual DOM updates. Just: WS message -> store -> UI.
 */

import { writable, derived } from 'svelte/store';
import type { OutcomeData, SnapshotMessage, UpdateMessage } from '../websocket/protocol';

export interface OddsSnapshot {
	sport: string;
	gameId: string;
	homeTeam: string;
	awayTeam: string;
	gameDescription: string;
	market: string | null;
	/** sportsbook -> outcome_key -> OutcomeData */
	odds: Record<string, Record<string, OutcomeData>>;
	loading: boolean;
}

const EMPTY_SNAPSHOT: OddsSnapshot = {
	sport: '',
	gameId: '',
	homeTeam: '',
	awayTeam: '',
	gameDescription: '',
	market: null,
	odds: {},
	loading: false,
};

export const oddsData = writable<OddsSnapshot>({ ...EMPTY_SNAPSHOT });

/**
 * Apply a full snapshot from the backend (replaces all data).
 */
export function applySnapshot(msg: SnapshotMessage): void {
	oddsData.set({
		sport: msg.sport,
		gameId: msg.game_id,
		homeTeam: msg.home_team,
		awayTeam: msg.away_team,
		gameDescription: msg.game_description,
		market: msg.market,
		odds: msg.odds,
		loading: false,
	});
}

/**
 * Apply an incremental update from the backend (merges into existing data).
 *
 * EDUCATIONAL: The backend sends a full snapshot for each updated sportsbook
 * (via StateStore.get_snapshot), so we REPLACE each sportsbook's outcomes
 * entirely rather than deep-merging keys.  This ensures that outcomes/books
 * removed from the backend (e.g., suspended odds) are also removed on the
 * frontend.  Sportsbooks NOT present in the message are left untouched.
 */
export function applyUpdate(msg: UpdateMessage): void {
	oddsData.update((current) => {
		const updatedOdds = { ...current.odds };

		// The message contains the complete current state for every sportsbook
		// included in msg.odds.  Replace each one wholesale.
		for (const [sportsbook, outcomes] of Object.entries(msg.odds)) {
			// Filter out any outcomes with null odds (suspended) just in case
			const live: Record<string, OutcomeData> = {};
			for (const [key, outcome] of Object.entries(outcomes)) {
				if (outcome.odds !== null) {
					live[key] = outcome;
				}
			}
			if (Object.keys(live).length > 0) {
				updatedOdds[sportsbook] = live;
			} else {
				delete updatedOdds[sportsbook];
			}
		}

		// Remove sportsbooks that are no longer present in a full-game update.
		// msg.odds is a full snapshot for this game/market, so any sportsbook
		// absent from it has no data for this market anymore.
		for (const book of Object.keys(updatedOdds)) {
			if (!(book in msg.odds)) {
				delete updatedOdds[book];
			}
		}

		return { ...current, odds: updatedOdds };
	});
}

export function clearOdds(): void {
	oddsData.set({ ...EMPTY_SNAPSHOT });
}

export function setLoading(): void {
	oddsData.update((current) => ({ ...current, loading: true, odds: {} }));
}

/**
 * Derived store: list of sportsbooks that have data.
 */
export const activeSportsbooks = derived(oddsData, ($odds) =>
	Object.keys($odds.odds).sort()
);

/**
 * Derived store: organized rows for the odds grid.
 *
 * Groups outcomes by their display label (e.g., "O 5.5", "U 5.5")
 * across all sportsbooks, making it easy to render a comparison table.
 */
export interface OddsRow {
	label: string;
	outcomeName: string;
	outcomeLine: string | null;
	overUnder: string | null;
	target: string | null;
	/** sportsbook -> odds data for this row */
	cells: Record<string, OutcomeData>;
	/** Which sportsbook has the best odds in this row */
	bestBook: string | null;
	/** Groups paired outcomes (e.g. both sides of a spread) for visual grouping */
	pairId: string;
}

/**
 * Compute a pair identifier that groups complementary outcomes together.
 * For spreads: both sides share the same absolute line value.
 * For totals: over and under share the same line value.
 * For moneyline: all outcomes share a single group.
 */
function computePairId(outcome: { outcome_name: string; outcome_line: string | null }): string {
	const name = outcome.outcome_name?.toLowerCase() ?? '';
	if (name === 'spread' && outcome.outcome_line) {
		return `spread_${Math.abs(parseFloat(outcome.outcome_line))}`;
	}
	if (name === 'total' && outcome.outcome_line) {
		return `total_${outcome.outcome_line}`;
	}
	return `other_${name}`;
}

export const oddsRows = derived(oddsData, ($odds): OddsRow[] => {
	const rowMap = new Map<string, OddsRow>();

	for (const [sportsbook, outcomes] of Object.entries($odds.odds)) {
		for (const [key, outcome] of Object.entries(outcomes)) {
			// Build a human-readable label for grouping
			let label = outcome.outcome_name || '';
			if (outcome.outcome_over_under && outcome.outcome_line) {
				label = `${outcome.outcome_over_under === 'O' ? 'Over' : 'Under'} ${outcome.outcome_line}`;
			} else if (outcome.outcome_target) {
				label = outcome.outcome_target;
				if (outcome.outcome_line) {
					label += ` ${outcome.outcome_line}`;
				}
			}

			// Use the outcome key as the unique row identifier
			const rowKey = key;

			if (!rowMap.has(rowKey)) {
				rowMap.set(rowKey, {
					label,
					outcomeName: outcome.outcome_name,
					outcomeLine: outcome.outcome_line,
					overUnder: outcome.outcome_over_under,
					target: outcome.outcome_target,
					cells: {},
					bestBook: null,
					pairId: computePairId(outcome),
				});
			}

			const row = rowMap.get(rowKey)!;
			if (outcome.odds) {
				row.cells[sportsbook] = outcome;
			}
		}
	}

	// Calculate best odds for each row
	for (const row of rowMap.values()) {
		let bestOdds = -Infinity;
		let bestBook: string | null = null;

		for (const [book, cell] of Object.entries(row.cells)) {
			if (!cell.odds) continue;
			const numericOdds = parseInt(cell.odds, 10);
			if (!isNaN(numericOdds) && numericOdds > bestOdds) {
				bestOdds = numericOdds;
				bestBook = book;
			}
		}
		row.bestBook = bestBook;
	}

	// Sort rows: group by pair, then within each pair order logically
	const rows = Array.from(rowMap.values());
	rows.sort((a, b) => {
		// First: group by pairId
		if (a.pairId !== b.pairId) {
			// For spread pairs, sort by absolute line (smallest spread first)
			const absLineA = a.outcomeLine ? Math.abs(parseFloat(a.outcomeLine)) : 0;
			const absLineB = b.outcomeLine ? Math.abs(parseFloat(b.outcomeLine)) : 0;
			if (absLineA !== absLineB) return absLineA - absLineB;
			return a.pairId.localeCompare(b.pairId);
		}
		// Within a pair: favorite (negative line) first for spreads
		const lineA = a.outcomeLine ? parseFloat(a.outcomeLine) : 0;
		const lineB = b.outcomeLine ? parseFloat(b.outcomeLine) : 0;
		if (lineA !== lineB) return lineA - lineB;
		// Over before Under for totals
		if (a.overUnder === 'O' && b.overUnder === 'U') return -1;
		if (a.overUnder === 'U' && b.overUnder === 'O') return 1;
		return a.label.localeCompare(b.label);
	});

	return rows;
});
