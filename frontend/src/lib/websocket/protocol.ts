/**
 * WebSocket message protocol types.
 *
 * These TypeScript interfaces define the contract between our FastAPI backend
 * and Svelte frontend. They mirror the message types defined in ws_routes.py.
 *
 * EDUCATIONAL: Having typed message protocols prevents bugs where frontend
 * and backend disagree on field names or types. In production systems, you'd
 * often generate these from a shared schema (e.g., OpenAPI, protobuf).
 */

// ============================================================================
// Frontend -> Backend Messages
// ============================================================================

export interface SubscribeMessage {
	type: 'subscribe';
	sport: string;
	game_id: string;
	market: string;
}

export interface UnsubscribeMessage {
	type: 'unsubscribe';
}

export interface PingMessage {
	type: 'ping';
}

export type ClientMessage = SubscribeMessage | UnsubscribeMessage | PingMessage;

// ============================================================================
// Backend -> Frontend Messages
// ============================================================================

export interface OutcomeData {
	odds: string | null;
	outcome_name: string;
	outcome_line: string | null;
	outcome_over_under: string | null;
	outcome_target: string | null;
	previous_odds: string | null;
	timestamp: string;
}

export interface ConnectedMessage {
	type: 'connected';
	server_time: string;
}

export interface SnapshotMessage {
	type: 'snapshot';
	sport: string;
	game_id: string;
	home_team: string;
	away_team: string;
	game_description: string;
	market: string | null;
	odds: Record<string, Record<string, OutcomeData>>;
}

export interface UpdateMessage {
	type: 'update';
	sport: string;
	game_id: string;
	home_team: string;
	away_team: string;
	game_description: string;
	market: string | null;
	odds: Record<string, Record<string, OutcomeData>>;
}

export interface PongMessage {
	type: 'pong';
	server_time: string;
}

export interface StatusMessage {
	type: 'status';
	upstream_connected: boolean;
	games_tracked: number;
	sportsbooks_active: number;
}

export interface ErrorMessage {
	type: 'error';
	message: string;
}

export type ServerMessage =
	| ConnectedMessage
	| SnapshotMessage
	| UpdateMessage
	| PongMessage
	| StatusMessage
	| ErrorMessage;

// ============================================================================
// Shared Data Types
// ============================================================================

export interface GameInfo {
	game_id: string;
	home_team: string;
	away_team: string;
	sport: string;
	game_description: string;
	sportsbook_count: number;
	last_update: string;
}

export interface SportsResponse {
	sports: string[];
	sportsbooks: string[];
}

export interface GamesResponse {
	sport: string;
	games: GameInfo[];
}

export interface MarketsResponse {
	sport: string;
	game_id?: string;
	markets: string[];
}
