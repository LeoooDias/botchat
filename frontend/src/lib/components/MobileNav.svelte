<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { fly, fade } from 'svelte/transition';

	export let activePanel: 'none' | 'library' | 'chats' | 'newbot' | 'attachments' = 'none';
	export let hasConfiguredProviders = false;
	export let attachmentCount = 0;
	export let chatCount = 0;

	let showNewMenu = false;

	const dispatch = createEventDispatcher<{
		openPanel: 'library' | 'chats' | 'newbot' | 'attachments' | 'settings';
		closePanel: void;
		newChat: void;
	}>();

	function handleNavClick(panel: 'library' | 'chats' | 'newbot' | 'attachments' | 'settings') {
		if (panel === 'newbot') {
			// Toggle the New menu popup
			showNewMenu = !showNewMenu;
			return;
		}
		
		showNewMenu = false; // Close menu when switching panels
		
		if (panel === 'settings') {
			dispatch('openPanel', 'settings');
		} else if (activePanel === panel) {
			dispatch('closePanel');
		} else {
			dispatch('openPanel', panel);
		}
	}

	function handleNewBot() {
		showNewMenu = false;
		dispatch('openPanel', 'newbot');
	}

	function handleNewChat() {
		showNewMenu = false;
		dispatch('newChat');
	}

	function closeNewMenu() {
		showNewMenu = false;
	}

	const navItems = [
		{ id: 'library' as const, label: 'Bots' },
		{ id: 'chats' as const, label: 'Chats' },
		{ id: 'newbot' as const, label: 'New' },
		{ id: 'attachments' as const, label: 'Files' }
	];
</script>

<!-- Heroicon SVG components -->
{#snippet botIcon()}
	<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
		<path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
	</svg>
{/snippet}

{#snippet chatIcon()}
	<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
		<path stroke-linecap="round" stroke-linejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
	</svg>
{/snippet}

{#snippet plusIcon()}
	<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
		<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
	</svg>
{/snippet}

{#snippet paperclipIcon()}
	<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
		<path stroke-linecap="round" stroke-linejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
	</svg>
{/snippet}

<!-- Backdrop for New menu -->
{#if showNewMenu}
	<div
		class="fixed inset-0 z-40 md:hidden"
		on:click={closeNewMenu}
		on:keydown={(e) => e.key === 'Escape' && closeNewMenu()}
		role="button"
		tabindex="-1"
		transition:fade={{ duration: 150 }}
	></div>
{/if}

<nav
	class="fixed bottom-0 left-0 right-0 z-40 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 pb-safe md:hidden"
	in:fly={{ y: 100, duration: 200 }}
>
	<!-- New Menu Popup -->
	{#if showNewMenu}
		<div
			class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-white dark:bg-gray-800 rounded-xl shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden min-w-[160px]"
			transition:fly={{ y: 20, duration: 200 }}
		>
			<button
				on:click={handleNewBot}
				class="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition text-left text-gray-700 dark:text-gray-200"
			>
				{@render botIcon()}
				<span class="text-sm font-medium text-gray-900 dark:text-white">New Bot</span>
			</button>
			<div class="border-t border-gray-200 dark:border-gray-700"></div>
			<button
				on:click={handleNewChat}
				class="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700 transition text-left text-gray-700 dark:text-gray-200"
			>
				{@render chatIcon()}
				<span class="text-sm font-medium text-gray-900 dark:text-white">New Chat</span>
			</button>
		</div>
	{/if}

	<div class="flex items-center justify-around px-2 py-1">
		{#each navItems as item}
			<button
				on:click={() => handleNavClick(item.id)}
				class="flex flex-col items-center justify-center touch-target px-3 py-2 rounded-lg transition-colors relative mobile-tap-highlight
					{(activePanel === item.id || (item.id === 'newbot' && showNewMenu))
						? 'text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30' 
						: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'}"
				aria-label={item.label}
				aria-pressed={activePanel === item.id}
			>
				{#if item.id === 'library'}
					{@render botIcon()}
				{:else if item.id === 'chats'}
					{@render chatIcon()}
				{:else if item.id === 'newbot'}
					{@render plusIcon()}
				{:else if item.id === 'attachments'}
					{@render paperclipIcon()}
				{/if}
				<span class="text-[10px] mt-0.5 font-medium">{item.label}</span>
				
				<!-- Badge for attachments -->
				{#if item.id === 'attachments' && attachmentCount > 0}
					<span class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center bg-green-500 text-white text-[10px] font-bold rounded-full px-1">
						{attachmentCount > 9 ? '9+' : attachmentCount}
					</span>
				{/if}
				
				<!-- Badge for chats -->
				{#if item.id === 'chats' && chatCount > 0}
					<span class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] flex items-center justify-center bg-blue-500 text-white text-[10px] font-bold rounded-full px-1">
						{chatCount > 9 ? '9+' : chatCount}
					</span>
				{/if}

				<!-- Indicator for new bot if no providers -->
				{#if item.id === 'newbot' && !hasConfiguredProviders}
					<span class="absolute -top-0.5 -right-0.5 w-2 h-2 bg-amber-500 rounded-full"></span>
				{/if}
			</button>
		{/each}
	</div>
</nav>
