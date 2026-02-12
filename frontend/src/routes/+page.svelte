<!--
	Main dashboard page.

	Composes the selection flow (Sport -> Game -> Market) and the odds grid.
	When all three selections are made, subscribes via WebSocket for live data.

	EDUCATIONAL: Reactive Subscription
	=====================================
	We use Svelte's `$:` reactive declaration to watch the selections store.
	Whenever sport + game + market are all selected, we automatically send
	a WebSocket subscribe message. When the user changes any selection,
	we unsubscribe from the old data and subscribe to the new combination.

	This reactive pattern replaces imperative event handling:
	  Instead of: onClick -> if all selected -> subscribe
	  We use:     $: if (all selected) { subscribe() }
-->

<script lang="ts">
	import { getContext } from 'svelte';
	import { selections } from '$lib/stores/selections';
	import { clearOdds, setLoading } from '$lib/stores/odds';
	import { connectionState } from '$lib/stores/connection';
	import type { OddsWebSocketClient } from '$lib/websocket/client';
	import SportSelector from '$lib/components/SportSelector.svelte';
	import GameSelector from '$lib/components/GameSelector.svelte';
	import MarketSelector from '$lib/components/MarketSelector.svelte';
	import OddsGrid from '$lib/components/OddsGrid.svelte';

	const getWsClient = getContext<() => OddsWebSocketClient | null>('getWsClient');

	// Track the last subscription to avoid duplicate subscribes
	let lastSubscription = '';

	// Reactive: subscribe when all selections are made
	$: {
		const { sport, game, market } = $selections;
		const connected = $connectionState.state === 'connected';

		if (sport && game && market && connected) {
			const subKey = `${sport}:${game.game_id}:${market}`;
			if (subKey !== lastSubscription) {
				lastSubscription = subKey;
				setLoading();
				const client = getWsClient();
				client?.subscribe(sport, game.game_id, market);
			}
		} else if (!sport || !game || !market) {
			if (lastSubscription) {
				lastSubscription = '';
				clearOdds();
				const client = getWsClient();
				client?.unsubscribe();
			}
		}
	}

	// Re-subscribe on reconnection
	$: if ($connectionState.state === 'connected' && lastSubscription) {
		const { sport, game, market } = $selections;
		if (sport && game && market) {
			const client = getWsClient();
			client?.subscribe(sport, game.game_id, market);
		}
	}
</script>

<div class="dashboard">
	<section class="selectors">
		<SportSelector />
		<GameSelector />
		<MarketSelector />
	</section>

	<section class="odds-section">
		<OddsGrid />
	</section>
</div>

<style>
	.dashboard {
		max-width: 1400px;
		margin: 0 auto;
	}

	.selectors {
		border-bottom: 1px solid var(--color-border);
		padding-bottom: 8px;
	}

	.odds-section {
		padding-top: 8px;
	}
</style>
