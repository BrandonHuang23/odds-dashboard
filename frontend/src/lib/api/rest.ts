/**
 * REST API client for fetching metadata from the backend.
 *
 * These functions call the FastAPI REST endpoints to get lists of
 * available sports, games, and markets. This data is used to populate
 * the selection UI before the user subscribes via WebSocket.
 *
 * EDUCATIONAL: REST for metadata, WebSocket for live data.
 * REST is simpler and cacheable. We only use WebSocket when we need
 * continuous, real-time streaming.
 */

import type { SportsResponse, GamesResponse, MarketsResponse } from '../websocket/protocol';

const BASE_URL = '/api';

async function fetchJson<T>(url: string): Promise<T> {
	const response = await fetch(url);
	if (!response.ok) {
		throw new Error(`API error: ${response.status} ${response.statusText}`);
	}
	return response.json();
}

export async function fetchSports(): Promise<SportsResponse> {
	return fetchJson<SportsResponse>(`${BASE_URL}/sports`);
}

export async function fetchGames(sport: string): Promise<GamesResponse> {
	return fetchJson<GamesResponse>(`${BASE_URL}/games/${encodeURIComponent(sport)}`);
}

export async function fetchMarkets(sport: string, gameId?: string): Promise<MarketsResponse> {
	let url = `${BASE_URL}/markets/${encodeURIComponent(sport)}`;
	if (gameId) {
		url += `?game_id=${encodeURIComponent(gameId)}`;
	}
	return fetchJson<MarketsResponse>(url);
}
