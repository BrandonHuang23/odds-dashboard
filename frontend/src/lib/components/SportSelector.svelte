<!--
	Sport selector - horizontal pill buttons.

	Fetches available sports from the REST API on mount,
	then renders a pill for each. Clicking a pill selects that sport
	and triggers game/market list fetches.
-->

<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchSports } from '../api/rest';
	import { selections } from '../stores/selections';

	let sports: string[] = [];
	let loading = true;
	let error = '';

	onMount(async () => {
		try {
			const data = await fetchSports();
			sports = data.sports || [];
		} catch (e) {
			error = 'Failed to load sports';
			console.error(e);
		} finally {
			loading = false;
		}
	});

	function selectSport(sport: string) {
		selections.update((s) => ({
			sport,
			game: null,   // Reset downstream selections
			market: null,
		}));
	}

	$: selectedSport = $selections.sport;
</script>

<div class="sport-selector">
	{#if loading}
		<span class="loading-text">Loading sports...</span>
	{:else if error}
		<span class="error-text">{error}</span>
	{:else if sports.length === 0}
		<span class="empty-text">No sports available</span>
	{:else}
		{#each sports as sport}
			<button
				class="pill"
				class:active={selectedSport === sport}
				on:click={() => selectSport(sport)}
			>
				{sport}
			</button>
		{/each}
	{/if}
</div>

<style>
	.sport-selector {
		display: flex;
		gap: 8px;
		padding: 16px 24px;
		flex-wrap: wrap;
	}

	.pill {
		padding: 8px 20px;
		border-radius: 20px;
		background: var(--color-surface);
		color: var(--color-text-dim);
		border: 1px solid var(--color-border);
		font-weight: 500;
		transition: all 0.15s ease;
	}

	.pill:hover {
		background: var(--color-surface-hover);
		color: var(--color-text);
	}

	.pill.active {
		background: var(--color-accent);
		color: white;
		border-color: var(--color-accent);
	}

	.loading-text, .error-text, .empty-text {
		color: var(--color-text-muted);
		padding: 8px 0;
		font-size: 13px;
	}

	.error-text {
		color: var(--color-red);
	}
</style>
