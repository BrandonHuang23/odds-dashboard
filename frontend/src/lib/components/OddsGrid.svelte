<!--
	Main odds comparison grid.

	Displays a table with:
	  - Columns: one per sportsbook (DraftKings, FanDuel, etc.)
	  - Rows: one per outcome (Over 5.5, Under 5.5, etc.)
	  - Cells: American odds with movement indicators

	EDUCATIONAL: Reactive Rendering from WebSocket Data
	=====================================================
	This component subscribes to the `oddsRows` and `activeSportsbooks`
	derived stores. Whenever a WebSocket update changes the odds data,
	Svelte automatically re-derives the rows and re-renders only the
	cells that changed. No manual DOM diffing needed.
-->

<script lang="ts">
	import { oddsData, oddsRows, activeSportsbooks } from '../stores/odds';
	import OddsCell from './OddsCell.svelte';

	// Truncate long sportsbook names for column headers
	function shortBookName(name: string): string {
		const aliases: Record<string, string> = {
			'draftkings': 'DraftK.',
			'fanduel': 'FanDuel',
			'betmgm': 'BetMGM',
			'bovada': 'Bovada',
			'betrivers': 'BetRiv.',
			'pointsbetus': 'PtsBet',
			'betonlineag': 'BetOnl.',
			'betanysports': 'BetAny',
			'consensus': 'Consens.',
			'lowvig': 'LowVig',
			'espnbet': 'ESPN',
			'hardrockbet': 'HardRk.',
			'caesars': 'Caesars',
			'wynnbet': 'Wynn',
		};
		return aliases[name] || name.charAt(0).toUpperCase() + name.slice(1, 8);
	}

	$: books = $activeSportsbooks;
	$: rows = $oddsRows;
	$: isLoading = $oddsData.loading;
	$: hasData = rows.length > 0;
</script>

<div class="odds-grid-container">
	{#if isLoading}
		<div class="loading">
			<div class="spinner"></div>
			<p>Loading odds data...</p>
		</div>
	{:else if !hasData}
		<div class="empty">
			<p>Select a sport, game, and market to view odds</p>
		</div>
	{:else}
		<div class="table-scroll">
			<table>
				<thead>
					<tr>
						<th class="label-col">Outcome</th>
						{#each books as book}
							<th class="book-col" title={book}>{shortBookName(book)}</th>
						{/each}
					</tr>
				</thead>
				<tbody>
					{#each rows as row}
						<tr>
							<td class="row-label">{row.label}</td>
							{#each books as book}
								<OddsCell
									data={row.cells[book] || null}
									isBest={row.bestBook === book}
								/>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>

		<div class="legend">
			<span class="legend-item">
				<span class="arrow-sample up">&#9650;</span> odds improved
			</span>
			<span class="legend-item">
				<span class="arrow-sample down">&#9660;</span> odds worsened
			</span>
			<span class="legend-item">
				<span class="best-sample"></span> best odds
			</span>
		</div>
	{/if}
</div>

<style>
	.odds-grid-container {
		padding: 16px 24px;
	}

	.table-scroll {
		overflow-x: auto;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-lg);
	}

	table {
		width: 100%;
		border-collapse: collapse;
		min-width: 600px;
	}

	thead th {
		position: sticky;
		top: 0;
		background: var(--color-surface);
		padding: 10px 12px;
		text-align: center;
		font-size: 12px;
		font-weight: 600;
		color: var(--color-text-dim);
		text-transform: uppercase;
		letter-spacing: 0.3px;
		border-bottom: 2px solid var(--color-border);
		white-space: nowrap;
	}

	th.label-col {
		text-align: left;
		min-width: 120px;
	}

	th.book-col {
		min-width: 80px;
	}

	tbody tr {
		border-bottom: 1px solid var(--color-border);
		transition: background-color 0.1s ease;
	}

	tbody tr:last-child {
		border-bottom: none;
	}

	tbody tr:hover {
		background: var(--color-surface-hover);
	}

	td.row-label {
		padding: 8px 12px;
		font-weight: 600;
		font-size: 13px;
		color: var(--color-text);
		white-space: nowrap;
	}

	/* Loading state */
	.loading {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 60px 20px;
		color: var(--color-text-dim);
		gap: 16px;
	}

	.spinner {
		width: 32px;
		height: 32px;
		border: 3px solid var(--color-border);
		border-top-color: var(--color-accent);
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	/* Empty state */
	.empty {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 60px 20px;
		color: var(--color-text-muted);
	}

	/* Legend */
	.legend {
		display: flex;
		gap: 20px;
		padding: 12px 0 0;
		font-size: 11px;
		color: var(--color-text-muted);
	}

	.legend-item {
		display: flex;
		align-items: center;
		gap: 4px;
	}

	.arrow-sample {
		font-size: 9px;
	}

	.arrow-sample.up {
		color: var(--color-green);
	}

	.arrow-sample.down {
		color: var(--color-red);
	}

	.best-sample {
		width: 14px;
		height: 14px;
		background: var(--color-best);
		border-radius: 3px;
		border: 1px solid var(--color-green);
	}
</style>
