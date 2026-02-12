/**
 * WebSocket client with automatic reconnection.
 *
 * EDUCATIONAL: Client-Side WebSocket Lifecycle
 * ==============================================
 * The browser's WebSocket API provides four event handlers:
 *
 *   onopen    - Connection established. Now safe to send messages.
 *   onmessage - Server sent us data. Parse and process it.
 *   onclose   - Connection closed (cleanly or not). Decide whether to reconnect.
 *   onerror   - An error occurred. Usually followed by onclose.
 *
 * Key gotchas:
 *   - You CANNOT send messages before onopen fires
 *   - onclose fires for BOTH intentional and accidental disconnects
 *   - The browser does NOT auto-reconnect. You must implement it yourself.
 *   - WebSocket connections can silently die (NAT timeout, proxy timeout).
 *     Heartbeat/ping-pong detects these "zombie" connections.
 *
 * Reconnection Strategy: Exponential Backoff
 * ============================================
 * When the connection drops, we retry with increasing delays:
 *   1s -> 2s -> 4s -> 8s -> 16s -> 30s (max)
 *
 * This prevents hammering the server during outages and allows time for
 * network issues to resolve. The delay resets on successful connection.
 */

import type { ClientMessage, ServerMessage } from './protocol';

export type ConnectionState = 'disconnected' | 'connecting' | 'connected';
export type MessageHandler = (message: ServerMessage) => void;
export type StateChangeHandler = (state: ConnectionState) => void;

export class OddsWebSocketClient {
	private ws: WebSocket | null = null;
	private url: string;
	private reconnectDelay = 1000; // Start at 1 second
	private maxReconnectDelay = 30000; // Max 30 seconds
	private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
	private pingInterval: ReturnType<typeof setInterval> | null = null;
	private intentionalClose = false;

	private onMessage: MessageHandler;
	private onStateChange: StateChangeHandler;

	constructor(
		url: string,
		onMessage: MessageHandler,
		onStateChange: StateChangeHandler
	) {
		this.url = url;
		this.onMessage = onMessage;
		this.onStateChange = onStateChange;
	}

	/**
	 * Initiate the WebSocket connection.
	 *
	 * EDUCATIONAL: `new WebSocket(url)` immediately starts the connection
	 * handshake. The constructor is non-blocking - you must wait for the
	 * `onopen` event before sending any messages.
	 */
	connect(): void {
		if (this.ws?.readyState === WebSocket.OPEN || this.ws?.readyState === WebSocket.CONNECTING) {
			return; // Already connected or connecting
		}

		this.intentionalClose = false;
		this.onStateChange('connecting');

		this.ws = new WebSocket(this.url);

		this.ws.onopen = () => {
			console.log('[WS] Connected to backend');
			this.onStateChange('connected');
			this.reconnectDelay = 1000; // Reset backoff on success
			this.startHeartbeat();
		};

		this.ws.onmessage = (event: MessageEvent) => {
			try {
				const message: ServerMessage = JSON.parse(event.data);
				this.onMessage(message);
			} catch (e) {
				console.error('[WS] Failed to parse message:', e);
			}
		};

		this.ws.onclose = (event: CloseEvent) => {
			console.log(`[WS] Connection closed: code=${event.code} reason=${event.reason}`);
			this.onStateChange('disconnected');
			this.stopHeartbeat();

			// Reconnect unless we intentionally closed
			if (!this.intentionalClose) {
				this.scheduleReconnect();
			}
		};

		this.ws.onerror = (event: Event) => {
			// onerror fires before onclose. We handle reconnection in onclose.
			console.error('[WS] Connection error');
		};
	}

	/**
	 * Send a typed message to the backend.
	 *
	 * EDUCATIONAL: WebSocket.send() can throw if the connection isn't open.
	 * Always check readyState before sending, or queue messages to send
	 * after reconnection.
	 */
	send(message: ClientMessage): void {
		if (this.ws?.readyState !== WebSocket.OPEN) {
			console.warn('[WS] Cannot send - not connected');
			return;
		}
		this.ws.send(JSON.stringify(message));
	}

	/**
	 * Subscribe to a specific sport/game/market combination.
	 */
	subscribe(sport: string, gameId: string, market: string): void {
		this.send({
			type: 'subscribe',
			sport,
			game_id: gameId,
			market,
		});
	}

	/**
	 * Unsubscribe from current data stream.
	 */
	unsubscribe(): void {
		this.send({ type: 'unsubscribe' });
	}

	/**
	 * Intentionally close the connection (no auto-reconnect).
	 */
	disconnect(): void {
		this.intentionalClose = true;
		this.stopHeartbeat();
		if (this.reconnectTimer) {
			clearTimeout(this.reconnectTimer);
			this.reconnectTimer = null;
		}
		if (this.ws) {
			this.ws.close(1000, 'Client closing');
			this.ws = null;
		}
	}

	/**
	 * Schedule a reconnection attempt with exponential backoff.
	 *
	 * EDUCATIONAL: Exponential backoff prevents "thundering herd" - when
	 * a server restarts, all clients reconnecting simultaneously can
	 * overwhelm it. By spacing out retries, the load is distributed.
	 */
	private scheduleReconnect(): void {
		console.log(`[WS] Reconnecting in ${this.reconnectDelay / 1000}s...`);

		this.reconnectTimer = setTimeout(() => {
			this.connect();
		}, this.reconnectDelay);

		// Increase delay for next attempt (exponential backoff)
		this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
	}

	/**
	 * Start periodic heartbeat to detect zombie connections.
	 *
	 * EDUCATIONAL: WebSocket connections can silently die when a network
	 * intermediary (NAT, proxy, firewall) drops the TCP connection without
	 * notifying either endpoint. Periodic pings detect this: if we don't
	 * get a pong within the expected timeframe, we know the connection is dead.
	 */
	private startHeartbeat(): void {
		this.stopHeartbeat();
		this.pingInterval = setInterval(() => {
			this.send({ type: 'ping' });
		}, 30000); // Ping every 30 seconds
	}

	private stopHeartbeat(): void {
		if (this.pingInterval) {
			clearInterval(this.pingInterval);
			this.pingInterval = null;
		}
	}
}
