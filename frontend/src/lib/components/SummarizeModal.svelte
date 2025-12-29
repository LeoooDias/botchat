<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';

	interface Bot {
		id: string;
		name?: string;
		provider: string;
		model: string;
	}

	export let isOpen = false;
	export let savedBots: Bot[] = [];
	export let activeBots: Bot[] = [];
	export let isLoading = false;

	const dispatch = createEventDispatcher<{ summarize: string; close: void }>();

	let selectedBotId: string = '';

	$: conversationBotKeys = activeBots.map(b => `${b.provider}:${b.model}:${b.name || ''}`);
	$: conversationBots = savedBots
		.filter(b => conversationBotKeys.includes(`${b.provider}:${b.model}:${b.name || ''}`))
		.sort((a, b) => (a.name || a.model).localeCompare(b.name || b.model));
	$: otherBots = savedBots
		.filter(b => !conversationBotKeys.includes(`${b.provider}:${b.model}:${b.name || ''}`))
		.sort((a, b) => (a.name || a.model).localeCompare(b.name || b.model));

	function handleSummarize() {
		if (selectedBotId) {
			dispatch('summarize', selectedBotId);
		}
	}

	function handleClose() {
		selectedBotId = '';
		dispatch('close');
	}

	onMount(() => {
		function handleKeyDown(e: KeyboardEvent) {
			if (e.key === 'Escape' && isOpen) {
				handleClose();
			}
		}

		window.addEventListener('keydown', handleKeyDown);
		return () => window.removeEventListener('keydown', handleKeyDown);
	});

</script>

{#if isOpen}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 w-full max-w-md mx-4">
			<h2 class="text-lg font-bold text-gray-900 dark:text-white mb-4">
				{#if isLoading}
					Summarizing Chat
				{:else}
					Summarize Chat
				{/if}
			</h2>

			{#if isLoading}
				<!-- Loading State -->
				<div class="flex flex-col items-center justify-center py-8">
					<div class="animate-spin mb-4">
						<svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
					</div>
					<p class="text-gray-600 dark:text-gray-300 text-center mb-2">
						Generating summary using <span class="font-semibold">{savedBots.find((b) => b.id === selectedBotId)?.name || 'selected bot'}</span>...
					</p>
					<p class="text-xs text-gray-500 dark:text-gray-400 text-center">
						This may take a few moments depending on chat length and model complexity.
					</p>
				</div>
			{:else if savedBots.length === 0}
				<p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
					No saved bots available. Please create a bot first.
				</p>
			{:else}
				<div class="mb-6">
					<label for="bot-select" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
						Select a bot to summarize with:
					</label>
					<select
						id="bot-select"
						bind:value={selectedBotId}
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
					>
						<option value="">Choose a bot...</option>
						{#if conversationBots.length > 0}
							<optgroup label="In This Chat">
								{#each conversationBots as bot (bot.id)}
									<option value={bot.id}>
										{bot.name || 'Unnamed Bot'} · {bot.provider} / {bot.model}
									</option>
								{/each}
							</optgroup>
						{/if}
						{#if otherBots.length > 0}
							<optgroup label="All Bots">
								{#each otherBots as bot (bot.id)}
									<option value={bot.id}>
										{bot.name || 'Unnamed Bot'} · {bot.provider} / {bot.model}
									</option>
								{/each}
							</optgroup>
						{/if}
					</select>
				</div>

				<p class="text-xs text-gray-500 dark:text-gray-400 mb-6">
					The selected bot will receive the full chat and be asked to provide a summary limited to one printed page.
				</p>
			{/if}

			<!-- Buttons -->
			<div class="flex gap-2">
				{#if !isLoading}
					<button
						on:click={handleClose}
						class="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition font-medium text-sm"
					>
						Close
					</button>
				{/if}
				{#if !isLoading}
					<button
						on:click={handleSummarize}
						disabled={!selectedBotId || savedBots.length === 0}
						class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition font-medium text-sm"
					>
						Summarize
					</button>
				{/if}
			</div>
		</div>
	</div>
{/if}
