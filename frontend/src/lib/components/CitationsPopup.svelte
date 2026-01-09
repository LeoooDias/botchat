<script context="module" lang="ts">
	export interface Citation {
		index: number;
		url: string;
		title: string;
	}
</script>

<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let citations: Citation[] = [];
	export let isOpen = false;

	const dispatch = createEventDispatcher<{ close: void }>();

	function close() {
		dispatch('close');
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && isOpen) {
			close();
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			close();
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen && citations.length > 0}
	<!-- Backdrop -->
	<!-- svelte-ignore a11y_click_events_have_key_events -->
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div
		class="fixed inset-0 bg-black bg-opacity-30 z-40"
		on:click={handleBackdropClick}
	></div>
	
	<!-- Popup -->
	<div class="fixed bottom-16 left-1/2 -translate-x-1/2 z-50 w-full max-w-lg mx-4">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
			<!-- Header -->
			<div class="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
				<div class="flex items-center gap-2">
					<svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
					</svg>
					<h3 class="font-semibold text-gray-900 dark:text-white">
						Web Sources ({citations.length})
					</h3>
				</div>
				<button
					on:click={close}
					class="p-1 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition"
					title="Close"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Citations List -->
			<div class="max-h-64 overflow-y-auto">
				<ul class="divide-y divide-gray-100 dark:divide-gray-700">
					{#each citations as citation}
						<li class="hover:bg-gray-50 dark:hover:bg-gray-700/50 transition">
							<a
								href={citation.url}
								target="_blank"
								rel="noopener noreferrer"
								class="block px-4 py-3"
							>
								<div class="flex items-start gap-3">
									<span class="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 text-xs font-medium flex items-center justify-center">
										{citation.index}
									</span>
									<div class="flex-1 min-w-0">
										<p class="text-sm font-medium text-gray-900 dark:text-white truncate">
											{citation.title}
										</p>
										<p class="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
											{citation.url}
										</p>
									</div>
									<svg class="flex-shrink-0 w-4 h-4 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
									</svg>
								</div>
							</a>
						</li>
					{/each}
				</ul>
			</div>

			<!-- Footer -->
			<div class="px-4 py-2 bg-gray-50 dark:bg-gray-700/50 border-t border-gray-200 dark:border-gray-700">
				<p class="text-xs text-gray-500 dark:text-gray-400 text-center">
					Click a source to open in a new tab
				</p>
			</div>
		</div>
	</div>
{/if}
