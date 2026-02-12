<!--
	Root layout - initializes the WebSocket connection and provides
	it to all child components.

	EDUCATIONAL: Application-Level WebSocket Management
	=====================================================
	The WebSocket connection is created here in the root layout because
	it should live for the entire application lifetime. When the user
	navigates between pages (if we had multiple), the connection persists.

	We use Svelte's `onMount` (runs in browser only, not during SSR)
	to create the WebSocket client, and `onDestroy` to clean it up.
-->

<script lang="ts">
	import { onMount, onDestroy, setContext } from 'svelte';
	import { OddsWebSocketClient } from '$lib/websocket/client';
	import { connectionState } from '$lib/stores/connection';
	import { applySnapshot, applyUpdate } from '$lib/stores/odds';
	import type { ServerMessage } from '$lib/websocket/protocol';
	import Header from '$lib/components/Header.svelte';
	import '../app.css';

	let wsClient: OddsWebSocketClient | null = null;

	onMount(() => {
		// Determine WebSocket URL based on current location
		const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		const wsUrl = `${protocol}//${window.location.host}/ws/odds`;

		wsClient = new OddsWebSocketClient(
			wsUrl,
			handleMessage,
			handleStateChange
		);

		// Make the client available to child components via context
		setContext('wsClient', wsClient);

		// Connect!
		wsClient.connect();
	});

	onDestroy(() => {
		wsClient?.disconnect();
	});

	function handleMessage(message: ServerMessage): void {
		switch (message.type) {
			case 'connected':
				console.log('[App] Server connected at', message.server_time);
				break;

			case 'snapshot':
				applySnapshot(message);
				break;

			case 'update':
				applyUpdate(message);
				break;

			case 'status':
				connectionState.update((s) => ({
					...s,
					upstreamConnected: message.upstream_connected,
					gamesTracked: message.games_tracked,
					sportsbooksActive: message.sportsbooks_active,
				}));
				break;

			case 'pong':
				connectionState.update((s) => ({
					...s,
					lastPong: message.server_time,
				}));
				break;

			case 'error':
				console.error('[App] Server error:', message.message);
				break;
		}
	}

	function handleStateChange(state: 'disconnected' | 'connecting' | 'connected'): void {
		connectionState.update((s) => ({ ...s, state }));
	}

	// Export the client so +page.svelte can use it
	setContext('getWsClient', () => wsClient);
</script>

<div class="app">
	<Header />
	<main>
		<slot />
	</main>
</div>

<style>
	.app {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	main {
		flex: 1;
	}
</style>
