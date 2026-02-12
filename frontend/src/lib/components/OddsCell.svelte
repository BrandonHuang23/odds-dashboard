<!--
	A single cell in the odds comparison grid.

	Displays American odds with:
	  - Green/red movement arrows when odds change (fade after 3s)
	  - Green background highlight for best odds in the row
	  - Gray "--" for suspended/unavailable markets

	EDUCATIONAL: Svelte Transitions
	================================
	The `fade` transition on the movement arrow is pure Svelte magic.
	When the arrow element is added to the DOM, it fades in. When removed,
	it fades out. No manual CSS animation management needed.
-->

<script lang="ts">
	import type { OutcomeData } from '../websocket/protocol';
	import { onDestroy } from 'svelte';

	export let data: OutcomeData | null = null;
	export let isBest: boolean = false;

	// Movement tracking
	let movement: 'up' | 'down' | null = null;
	let movementTimer: ReturnType<typeof setTimeout> | null = null;

	// Detect movement when previous_odds differs from current
	$: if (data?.previous_odds && data.odds && data.previous_odds !== data.odds) {
		const prev = parseInt(data.previous_odds, 10);
		const curr = parseInt(data.odds, 10);
		if (!isNaN(prev) && !isNaN(curr)) {
			// Higher American odds = better for bettor
			movement = curr > prev ? 'up' : 'down';
			// Clear movement indicator after 3 seconds
			if (movementTimer) clearTimeout(movementTimer);
			movementTimer = setTimeout(() => { movement = null; }, 3000);
		}
	}

	onDestroy(() => {
		if (movementTimer) clearTimeout(movementTimer);
	});

	function formatOdds(odds: string): string {
		const num = parseInt(odds, 10);
		if (isNaN(num)) return odds;
		return num > 0 ? `+${num}` : `${num}`;
	}
</script>

<td class="odds-cell" class:best={isBest} class:suspended={!data?.odds}>
	{#if data?.odds}
		<span class="odds-value">{formatOdds(data.odds)}</span>
		{#if movement === 'up'}
			<span class="arrow up">&#9650;</span>
		{:else if movement === 'down'}
			<span class="arrow down">&#9660;</span>
		{/if}
	{:else}
		<span class="no-odds">--</span>
	{/if}
</td>

<style>
	.odds-cell {
		padding: 8px 12px;
		text-align: center;
		font-family: var(--font-mono);
		font-size: 13px;
		font-weight: 500;
		position: relative;
		transition: background-color 0.2s ease;
		white-space: nowrap;
	}

	.odds-cell.best {
		background: var(--color-best);
	}

	.odds-cell.suspended {
		opacity: 0.4;
	}

	.odds-value {
		color: var(--color-text);
	}

	.no-odds {
		color: var(--color-text-muted);
		font-style: italic;
	}

	.arrow {
		font-size: 9px;
		margin-left: 3px;
		animation: fadeInOut 3s ease forwards;
	}

	.arrow.up {
		color: var(--color-green);
	}

	.arrow.down {
		color: var(--color-red);
	}

	@keyframes fadeInOut {
		0% { opacity: 1; }
		70% { opacity: 1; }
		100% { opacity: 0; }
	}
</style>
