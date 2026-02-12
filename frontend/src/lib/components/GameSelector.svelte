<!--
	Game selector - card grid showing available games for the selected sport.

	Fetches games from the REST API when the selected sport changes.
	Each game is displayed as a clickable card showing "Away @ Home".
-->

<script lang="ts">
	import { fetchGames } from '../api/rest';
	import { selections } from '../stores/selections';
	import type { GameInfo } from '../websocket/protocol';

	let games: GameInfo[] = [];
	let loading = false;
	let error = '';

	// Track sport separately so the reactive block only fires on sport changes,
	// not on every selections update (e.g., game or market selection).
	let lastSport = '';
	$: currentSport = $selections.sport;
	$: if (currentSport !== lastSport) {
		lastSport = currentSport;
		if (currentSport) {
			loadGames(currentSport);
		} else {
			games = [];
		}
	}

	async function loadGames(sport: string) {
		loading = true;
		error = '';
		try {
			const data = await fetchGames(sport);
			games = data.games || [];
		} catch (e) {
			error = 'Failed to load games';
			console.error(e);
		} finally {
			loading = false;
		}
	}

	function selectGame(game: GameInfo) {
		selections.update((s) => ({
			...s,
			game,
			market: null, // Reset market when game changes
		}));
	}

	$: selectedGameId = $selections.game?.game_id;
</script>

{#if $selections.sport}
	<div class="game-selector">
		<h3 class="section-title">Select a game</h3>
		{#if loading}
			<p class="loading-text">Loading games...</p>
		{:else if error}
			<p class="error-text">{error}</p>
		{:else if games.length === 0}
			<p class="empty-text">No games available for {$selections.sport}</p>
		{:else}
			<div class="game-grid">
				{#each games as game}
					<button
						class="game-card"
						class:active={selectedGameId === game.game_id}
						on:click={() => selectGame(game)}
					>
						<span class="teams">
							{game.away_team} @ {game.home_team}
						</span>
						<span class="meta">
							{game.sportsbook_count} sportsbooks
						</span>
					</button>
				{/each}
			</div>
		{/if}
	</div>
{/if}

<style>
	.game-selector {
		padding: 0 24px 16px;
	}

	.section-title {
		font-size: 13px;
		font-weight: 500;
		color: var(--color-text-dim);
		text-transform: uppercase;
		letter-spacing: 0.5px;
		margin-bottom: 12px;
	}

	.game-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
		gap: 10px;
	}

	.game-card {
		display: flex;
		flex-direction: column;
		gap: 4px;
		padding: 14px 16px;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius);
		text-align: left;
		transition: all 0.15s ease;
	}

	.game-card:hover {
		background: var(--color-surface-hover);
		border-color: var(--color-text-muted);
	}

	.game-card.active {
		border-color: var(--color-accent);
		background: rgba(59, 130, 246, 0.08);
	}

	.teams {
		font-weight: 600;
		color: var(--color-text);
		font-size: 14px;
	}

	.meta {
		font-size: 12px;
		color: var(--color-text-muted);
	}

	.loading-text, .error-text, .empty-text {
		color: var(--color-text-muted);
		font-size: 13px;
	}

	.error-text {
		color: var(--color-red);
	}
</style>
