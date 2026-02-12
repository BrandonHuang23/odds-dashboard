/**
 * WebSocket connection state store.
 *
 * Tracks the current connection status (disconnected/connecting/connected)
 * and system metrics (games tracked, sportsbooks active).
 *
 * EDUCATIONAL: Svelte stores are reactive containers. When you write
 * `$connectionState` in a component, Svelte automatically subscribes
 * to changes and re-renders the component when the value updates.
 * This is how WebSocket events trigger UI updates without manual DOM work.
 */

import { writable } from 'svelte/store';
import type { ConnectionState } from '../websocket/client';

export interface ConnectionInfo {
	state: ConnectionState;
	upstreamConnected: boolean;
	gamesTracked: number;
	sportsbooksActive: number;
	lastPong: string | null;
}

export const connectionState = writable<ConnectionInfo>({
	state: 'disconnected',
	upstreamConnected: false,
	gamesTracked: 0,
	sportsbooksActive: 0,
	lastPong: null,
});
