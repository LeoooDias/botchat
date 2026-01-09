<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { slide } from 'svelte/transition';
	import { isBotModelValid, validateBotModel } from '$lib/modelLimits';

	interface Bot {
		id: string;
		provider: string;
		model: string;
		name?: string;
		maxTokens?: number;
		systemInstructionText?: string;
		category?: string;
		webSearchEnabled?: boolean;
	}

	export let activeBots: Bot[] = [];
	export let expanded = true;
	export let globalMaxTokens = 4000;

	const dispatch = createEventDispatcher<{
		remove: string;
		removeAll: void;
		toggle: void;
		edit: Bot;
	}>();

	function getProviderColor(provider: string, valid: boolean): string {
		if (!valid) {
			return 'bg-red-100 dark:bg-red-900/40 border-red-400 dark:border-red-600 text-red-800 dark:text-red-200';
		}
		const colors: Record<string, string> = {
			'openai': 'bg-green-100 dark:bg-green-900/40 border-green-300 dark:border-green-700 text-green-800 dark:text-green-200',
			'anthropic': 'bg-orange-100 dark:bg-orange-900/40 border-orange-300 dark:border-orange-700 text-orange-800 dark:text-orange-200',
			'gemini': 'bg-blue-100 dark:bg-blue-900/40 border-blue-300 dark:border-blue-700 text-blue-800 dark:text-blue-200'
		};
		return colors[provider.toLowerCase()] || 'bg-gray-100 dark:bg-gray-700 border-gray-300 dark:border-gray-600 text-gray-800 dark:text-gray-200';
	}
</script>

{#if activeBots.length > 0}
	<div class="border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
		<!-- Header / Toggle -->
		<div class="w-full flex items-center justify-between px-4 py-2">
			<button
				on:click={() => dispatch('toggle')}
				class="flex items-center gap-2 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition touch-target rounded px-2 py-1 -ml-2"
			>
				<span class="text-sm text-gray-500 dark:text-gray-400">
					{expanded ? '▼' : '▶'}
				</span>
				<span class="text-sm font-medium text-gray-700 dark:text-gray-300">
					{activeBots.length} active {activeBots.length === 1 ? 'bot' : 'bots'}
				</span>
			</button>
			{#if expanded && activeBots.length > 1}
				<button
					on:click={() => dispatch('removeAll')}
					class="text-xs text-gray-500 dark:text-gray-400 hover:text-red-500 dark:hover:text-red-400 px-2 py-1 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition"
				>
					Remove all
				</button>
			{/if}
		</div>

		<!-- Bot chips -->
		{#if expanded}
			<div class="px-4 pb-3" transition:slide={{ duration: 200 }}>
				<div class="flex gap-2 overflow-x-auto mobile-scroll mobile-hide-scrollbar pb-1 -mx-4 px-4">
					{#each activeBots as bot (bot.id)}
						{@const botValid = isBotModelValid(bot)}
						<div
							class="flex items-center gap-2 px-3 py-2 rounded-lg border flex-shrink-0 {getProviderColor(bot.provider, botValid)}"
						>
							{#if !botValid}
								<svg class="w-4 h-4 text-red-500 dark:text-red-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
									<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
								</svg>
							{/if}
							<button
								on:click={() => dispatch('edit', bot)}
								class="flex flex-col min-w-0 text-left active:opacity-70 transition"
							>
								<span class="text-xs font-medium truncate max-w-[120px] flex items-center gap-1">
									{bot.name || bot.provider}
									{#if bot.webSearchEnabled}
										<svg class="w-3 h-3 text-blue-500 dark:text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
											<title>Web search enabled</title>
											<path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
										</svg>
									{/if}
								</span>
								<span class="text-[10px] opacity-75 truncate max-w-[120px] {!botValid ? 'line-through' : ''}">
									{bot.model}
								</span>
								{#if !botValid}
									<span class="text-[10px] text-red-600 dark:text-red-400 font-medium">
										Tap to fix
									</span>
								{:else}
									<span class="text-[10px] opacity-60">
										{bot.maxTokens || globalMaxTokens} tokens
									</span>
								{/if}
							</button>
							<button
								on:click={() => dispatch('remove', bot.id)}
								class="ml-1 w-5 h-5 flex items-center justify-center text-current opacity-60 hover:opacity-100 hover:text-red-500 dark:hover:text-red-400 rounded-full hover:bg-black/10 dark:hover:bg-white/10 transition"
								aria-label="Remove {bot.name || bot.model}"
							>
								×
							</button>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>
{/if}
