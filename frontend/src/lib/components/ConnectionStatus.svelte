<!--
	Connection status indicator dot.

	Shows the current state of the WebSocket connection:
	  Green pulsing = connected and receiving data
	  Yellow        = connected but stale (no recent data)
	  Red           = disconnected
	  Animated      = connecting/reconnecting
-->

<script lang="ts">
	import { connectionState } from '../stores/connection';

	$: state = $connectionState.state;
	$: statusText = state === 'connected' ? 'Connected'
		: state === 'connecting' ? 'Connecting...'
		: 'Disconnected';
	$: statusClass = state === 'connected' ? 'connected'
		: state === 'connecting' ? 'connecting'
		: 'disconnected';
</script>

<div class="status" title={statusText}>
	<span class="dot {statusClass}"></span>
	<span class="label">{statusText}</span>
	{#if state === 'connected' && $connectionState.gamesTracked > 0}
		<span class="meta">{$connectionState.gamesTracked} games</span>
	{/if}
</div>

<style>
	.status {
		display: flex;
		align-items: center;
		gap: 6px;
		font-size: 12px;
		color: var(--color-text-dim);
	}

	.dot {
		width: 8px;
		height: 8px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.dot.connected {
		background: var(--color-green);
		box-shadow: 0 0 6px var(--color-green);
		animation: pulse 2s ease-in-out infinite;
	}

	.dot.connecting {
		background: var(--color-yellow);
		animation: pulse 0.8s ease-in-out infinite;
	}

	.dot.disconnected {
		background: var(--color-red);
	}

	.meta {
		color: var(--color-text-muted);
		margin-left: 4px;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}
</style>
