/**
 * User selection state store.
 *
 * Tracks what the user has currently selected: sport, game, and market.
 * When all three are selected, the app subscribes via WebSocket to get
 * live odds for that combination.
 */

import { writable } from 'svelte/store';
import type { GameInfo } from '../websocket/protocol';

export interface SelectionState {
	sport: string | null;
	game: GameInfo | null;
	market: string | null;
}

export const selections = writable<SelectionState>({
	sport: null,
	game: null,
	market: null,
});
