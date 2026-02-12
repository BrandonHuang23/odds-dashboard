<!--
	Loading indicator shown during the initial data burst.

	EDUCATIONAL: Initial Burst Pattern
	====================================
	After subscribing to BoltOdds, the server dumps 100+ messages
	containing the current state. This is the "initial burst" phase.
	We show a loading indicator until data stabilizes.
-->

<script lang="ts">
	import { oddsData, activeSportsbooks } from '../stores/odds';

	$: isLoading = $oddsData.loading;
	$: bookCount = $activeSportsbooks.length;
</script>

{#if isLoading}
	<div class="burst-loading">
		<div class="spinner"></div>
		<p class="message">Loading odds data...</p>
		{#if bookCount > 0}
			<p class="detail">{bookCount} sportsbooks received</p>
		{/if}
	</div>
{/if}

<style>
	.burst-loading {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 40px 20px;
		gap: 12px;
	}

	.spinner {
		width: 28px;
		height: 28px;
		border: 3px solid var(--color-border);
		border-top-color: var(--color-accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.message {
		color: var(--color-text-dim);
		font-size: 14px;
	}

	.detail {
		color: var(--color-text-muted);
		font-size: 12px;
	}
</style>
