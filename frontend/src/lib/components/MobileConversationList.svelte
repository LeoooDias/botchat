<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { flip } from 'svelte/animate';
	import { fade, fly } from 'svelte/transition';

	interface Chat {
		id: string;
		name: string;
		description: string;
		createdAt: number;
		isPrivate: boolean;
	}

	export let chats: Chat[] = [];
	export let currentChatId = '';
	export let canCreateChat = true;
	export let maxChats = 3;
	export let isStreaming = false;

	const dispatch = createEventDispatcher<{
		select: string;
		delete: string;
		rename: { id: string; name: string };
	}>();

	let renamingId: string | null = null;
	let renameValue = '';
	let deleteConfirmId: string | null = null;

	// Swipe state for revealing actions
	let swipingId: string | null = null;
	let swipeOffset = 0;
	let startX = 0;
	let revealedId: string | null = null;
	const REVEAL_THRESHOLD = 70;
	const ACTION_WIDTH = 100;

	function handleSelect(id: string) {
		if (isStreaming && id !== currentChatId) return;
		if (renamingId || deleteConfirmId) return;
		dispatch('select', id);
	}

	function startRename(chat: Chat) {
		renamingId = chat.id;
		renameValue = chat.name;
	}

	function saveRename() {
		if (renamingId && renameValue.trim()) {
			dispatch('rename', { id: renamingId, name: renameValue.trim() });
		}
		renamingId = null;
		renameValue = '';
	}

	function cancelRename() {
		renamingId = null;
		renameValue = '';
	}

	function confirmDelete(id: string) {
		deleteConfirmId = id;
	}

	function executeDelete() {
		if (deleteConfirmId) {
			dispatch('delete', deleteConfirmId);
			deleteConfirmId = null;
		}
	}

	function cancelDelete() {
		deleteConfirmId = null;
	}

	// Touch handlers for swipe-to-delete
	function handleTouchStart(e: TouchEvent, id: string) {
		if (renamingId || deleteConfirmId) return;
		
		// If tapping on a different item, close the revealed one
		if (revealedId && revealedId !== id) {
			closeRevealedActions();
			return;
		}
		
		startX = e.touches[0].clientX;
		swipingId = id;
		
		// If this item is already revealed, keep its offset
		if (revealedId === id) {
			swipeOffset = -ACTION_WIDTH;
		} else {
			swipeOffset = 0;
		}
	}

	function handleTouchMove(e: TouchEvent) {
		if (!swipingId) return;
		const currentX = e.touches[0].clientX;
		let deltaX = currentX - startX;
		
		// If this item is already revealed, adjust the starting offset
		if (revealedId === swipingId) {
			deltaX = deltaX - ACTION_WIDTH;
		}
		
		// Only allow swipe left (negative), with some resistance past the action width
		swipeOffset = Math.min(0, Math.max(deltaX, -ACTION_WIDTH - 30));
	}

	function handleTouchEnd() {
		if (!swipingId) return;
		if (swipeOffset < -REVEAL_THRESHOLD) {
			// Snap to reveal actions
			revealedId = swipingId;
			swipeOffset = -ACTION_WIDTH;
		} else {
			// Snap back
			revealedId = null;
			swipeOffset = 0;
		}
		swipingId = null;
	}

	function closeRevealedActions() {
		revealedId = null;
		swipeOffset = 0;
	}

	function formatDate(timestamp: number): string {
		const date = new Date(timestamp);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

		if (diffDays === 0) {
			return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
		} else if (diffDays === 1) {
			return 'Yesterday';
		} else if (diffDays < 7) {
			return date.toLocaleDateString([], { weekday: 'short' });
		} else {
			return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
		}
	}
</script>

<div class="flex flex-col h-full">
	<!-- Header with limit info -->
	{#if !canCreateChat}
		<div class="p-3 border-b border-gray-200 dark:border-gray-700 bg-amber-50 dark:bg-amber-900/20">
			<p class="text-xs text-amber-600 dark:text-amber-400 text-center">
				Free limit: {maxChats} chats • Use New → Chat to create
			</p>
		</div>
	{/if}

	<!-- Chat list -->
	<div class="flex-1 overflow-y-auto mobile-scroll">
		{#if chats.length === 0}
			<div class="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400 px-4">
				<svg class="w-12 h-12 mb-3" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
				</svg>
				<p class="text-sm">No chats yet</p>
				<p class="text-xs mt-1">Tap New → Chat to start</p>
			</div>
		{:else}
			<ul class="divide-y divide-gray-200 dark:divide-gray-700">
				{#each chats as chat (chat.id)}
					<li
						animate:flip={{ duration: 200 }}
						class="relative overflow-hidden"
					>
						<!-- Action buttons background -->
						<div class="absolute inset-y-0 right-0 w-[100px] flex">
							<button
								on:click|stopPropagation={() => { closeRevealedActions(); startRename(chat); }}
								class="flex-1 bg-blue-500 flex items-center justify-center"
								aria-label="Rename"
							>
								<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
								</svg>
							</button>
							<button
								on:click|stopPropagation={() => { closeRevealedActions(); confirmDelete(chat.id); }}
								class="flex-1 bg-red-500 flex items-center justify-center"
								aria-label="Delete"
							>
								<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
								</svg>
							</button>
						</div>

						<!-- Chat item -->
						<div
							class="relative bg-white dark:bg-gray-800 transition-transform duration-150 ease-out"
							style="transform: translateX({swipingId === chat.id ? swipeOffset : (revealedId === chat.id ? -ACTION_WIDTH : 0)}px)"
							on:touchstart={(e) => handleTouchStart(e, chat.id)}
							on:touchmove={handleTouchMove}
							on:touchend={handleTouchEnd}
							role="button"
							tabindex="0"
						>
							{#if renamingId === chat.id}
								<!-- Rename mode -->
								<div class="p-4 flex items-center gap-2">
									<input
										type="text"
										bind:value={renameValue}
										on:keydown={(e) => {
											if (e.key === 'Enter') saveRename();
											if (e.key === 'Escape') cancelRename();
										}}
										class="flex-1 px-3 py-2 border border-blue-500 rounded-lg text-sm bg-white dark:bg-gray-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
									/>
									<button
										on:click={saveRename}
										class="p-2 text-green-600 dark:text-green-400 touch-target"
									>
										✓
									</button>
									<button
										on:click={cancelRename}
										class="p-2 text-gray-500 touch-target"
									>
										✕
									</button>
								</div>
							{:else}
								<!-- Normal view -->
								<button
									on:click={() => handleSelect(chat.id)}
									class="w-full p-4 text-left transition hover:bg-gray-50 dark:hover:bg-gray-700/50
										{currentChatId === chat.id ? 'bg-blue-50 dark:bg-blue-900/30 border-l-4 border-blue-500' : ''}
										{isStreaming && currentChatId !== chat.id ? 'opacity-50' : ''}"
									disabled={isStreaming && currentChatId !== chat.id}
								>
									<div class="flex items-start justify-between gap-2">
										<div class="flex-1 min-w-0">
											<h3 class="font-medium text-gray-900 dark:text-white truncate">
												{chat.name}
											</h3>
											{#if chat.description}
												<p class="text-sm text-gray-500 dark:text-gray-400 truncate mt-0.5">
													{chat.description}
												</p>
											{/if}
										</div>
										<span class="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
											{formatDate(chat.createdAt)}
										</span>
									</div>
								</button>


							{/if}
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	</div>

	<!-- Tip text -->
	<div class="p-2 border-t border-gray-200 dark:border-gray-700 text-center">
		<p class="text-xs text-gray-400 dark:text-gray-500">
			Swipe left on a chat for options
		</p>
	</div>
</div>

<!-- Delete confirmation modal -->
{#if deleteConfirmId}
	<div
		class="fixed inset-0 z-[60] bg-black/50 flex items-end justify-center pb-safe md:items-center"
		on:click={cancelDelete}
		on:keydown={(e) => e.key === 'Escape' && cancelDelete()}
		role="button"
		tabindex="-1"
		transition:fade={{ duration: 150 }}
	>
		<div
			class="bg-white dark:bg-gray-800 rounded-t-2xl md:rounded-2xl w-full max-w-sm mx-4 mb-4 md:mb-0 overflow-hidden shadow-2xl"
			on:click|stopPropagation
			on:keydown|stopPropagation
			role="dialog"
			tabindex="-1"
			aria-modal="true"
			transition:fly={{ y: 100, duration: 200 }}
		>
			<div class="p-6 text-center">
				<div class="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mx-auto mb-4">
					<svg class="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
					</svg>
				</div>
				<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Delete chat?</h3>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					This action cannot be undone.
				</p>
			</div>
			<div class="flex border-t border-gray-200 dark:border-gray-700">
				<button
					on:click={cancelDelete}
					class="flex-1 py-4 font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition touch-target"
				>
					Cancel
				</button>
				<button
					on:click={executeDelete}
					class="flex-1 py-4 font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 transition border-l border-gray-200 dark:border-gray-700 touch-target"
				>
					Delete
				</button>
			</div>
		</div>
	</div>
{/if}
