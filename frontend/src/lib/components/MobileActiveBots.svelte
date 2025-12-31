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
								<span class="text-xs font-medium truncate max-w-[120px]">
									{bot.name || bot.provider}
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
