<!--
	Application header with title and connection status.
-->

<script lang="ts">
	import ConnectionStatus from './ConnectionStatus.svelte';
</script>

<header>
	<div class="title">
		<h1>Odds Dashboard</h1>
	</div>
	<ConnectionStatus />
</header>

<style>
	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 12px 24px;
		background: var(--color-surface);
		border-bottom: 1px solid var(--color-border);
	}

	h1 {
		font-size: 18px;
		font-weight: 600;
		color: var(--color-text);
	}
</style>
