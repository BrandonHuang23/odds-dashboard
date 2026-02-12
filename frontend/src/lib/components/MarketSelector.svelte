<!--
	Market type selector - horizontal tabs (Total, Spread, Moneyline, etc.)

	Fetches available markets from the REST API when the selected game changes.
	When a market is selected, the app subscribes via WebSocket for live odds.
-->

<script lang="ts">
	import { fetchMarkets } from '../api/rest';
	import { selections } from '../stores/selections';

	let markets: string[] = [];
	let loading = false;
	let error = '';

	// Track game_id separately so the reactive block only fires on game changes,
	// not on every selections update (e.g., market tab click).
	let lastGameId = '';
	$: currentGameId = $selections.game?.game_id ?? '';
	$: currentSport = $selections.sport;
	$: if (currentGameId !== lastGameId) {
		lastGameId = currentGameId;
		if (currentSport && currentGameId) {
			loadMarkets(currentSport, currentGameId);
		} else {
			markets = [];
		}
	}

	async function loadMarkets(sport: string, gameId: string) {
		loading = true;
		error = '';
		try {
			const data = await fetchMarkets(sport, gameId);
			markets = data.markets || [];
		} catch (e) {
			error = 'Failed to load markets';
			console.error(e);
		} finally {
			loading = false;
		}
	}

	function selectMarket(market: string) {
		selections.update((s) => ({ ...s, market }));
	}

	$: selectedMarket = $selections.market;
</script>

{#if $selections.game}
	<div class="market-selector">
		<div class="game-header">
			{$selections.game.away_team} @ {$selections.game.home_team}
		</div>
		{#if loading}
			<span class="loading-text">Loading markets...</span>
		{:else if error}
			<span class="error-text">{error}</span>
		{:else if markets.length === 0}
			<span class="empty-text">No markets available</span>
		{:else}
			<div class="tabs">
				{#each markets as market}
					<button
						class="tab"
						class:active={selectedMarket === market}
						on:click={() => selectMarket(market)}
					>
						{market}
					</button>
				{/each}
			</div>
		{/if}
	</div>
{/if}

<style>
	.market-selector {
		padding: 0 24px 16px;
	}

	.game-header {
		font-size: 16px;
		font-weight: 600;
		color: var(--color-text);
		margin-bottom: 12px;
	}

	.tabs {
		display: flex;
		gap: 4px;
		border-bottom: 1px solid var(--color-border);
		padding-bottom: 0;
	}

	.tab {
		padding: 8px 16px;
		background: none;
		color: var(--color-text-dim);
		font-weight: 500;
		border-bottom: 2px solid transparent;
		margin-bottom: -1px;
		transition: all 0.15s ease;
	}

	.tab:hover {
		color: var(--color-text);
	}

	.tab.active {
		color: var(--color-accent);
		border-bottom-color: var(--color-accent);
	}

	.loading-text, .error-text, .empty-text {
		color: var(--color-text-muted);
		font-size: 13px;
	}

	.error-text {
		color: var(--color-red);
	}
</style>
