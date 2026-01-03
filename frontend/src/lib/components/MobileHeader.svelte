<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let chatName = '';
	export let isPaidUser = false;
	export let isAuthenticated = false;
	export let isSessionValid = false;
	export let messageCount = 0;
	export let responseModifier: 'none' | 'chat' | 'deep' = 'none';
	
	// Quota display props
	export let quotaUsed = 0;
	export let quotaLimit = 100;
	export let isQuotaExhausted = false;

	const dispatch = createEventDispatcher<{
		openSignIn: void;
		openSettings: void;
		openAbout: void;
		toggleModifier: void;
		exportChat: void;
		clearChat: void;
		summarizeChat: void;
	}>();
	
	// Show session expired warning if was authenticated but session is no longer valid
	$: showSessionExpired = isAuthenticated && !isSessionValid;

	let showChatMenu = false;
	let quotaElement: HTMLButtonElement;
	let tooltipTimeout: ReturnType<typeof setTimeout>;

	function handleMenuAction(action: () => void, keepOpen = false) {
		action();
		if (!keepOpen) {
			showChatMenu = false;
		}
	}

	function toggleQuotaTooltip() {
		if (quotaElement) {
			// Clear any existing timeout
			clearTimeout(tooltipTimeout);
			// Show tooltip
			quotaElement.classList.add('tooltip-visible');
			// Hide after 2 seconds
			tooltipTimeout = setTimeout(() => {
				quotaElement.classList.remove('tooltip-visible');
			}, 2000);
		}
	}
</script>

<!-- Mobile Header - Only visible on mobile (md:hidden) -->
<header class="relative bg-gradient-to-r from-blue-600 to-blue-700 dark:from-blue-800 dark:to-blue-900 text-white safe-top md:hidden z-30">
	<!-- Session Expired Banner -->
	{#if showSessionExpired}
		<button
			on:click={() => dispatch('openSignIn')}
			class="w-full bg-amber-500 text-amber-900 text-xs font-medium py-1.5 px-3 flex items-center justify-center gap-2"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
			</svg>
			<span>Session expired</span>
			<span class="underline">Sign in again</span>
		</button>
	{/if}
	
	<div class="flex items-center justify-between px-3 py-2">
		<!-- Left: Logo (tap to open About) -->
		<button
			on:click={() => dispatch('openAbout')}
			class="flex items-center"
			aria-label="About botchat"
		>
			<h1 class="text-lg font-extrabold">botchat</h1>
		</button>

		<!-- Center: Chat name (truncated) - clickable for chat menu -->
		<button
			on:click={() => (showChatMenu = !showChatMenu)}
			class="flex-1 mx-3 text-center overflow-hidden flex items-center justify-center gap-1"
		>
			<span class="text-sm font-medium truncate opacity-90">
				{chatName || 'New Chat'}
			</span>
			<svg class="w-3 h-3 opacity-70 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
			</svg>
		</button>

		<!-- Right: Quick actions -->
		<div class="flex items-center gap-1">
			<!-- Quota indicator (compact for mobile) -->
			{#if isAuthenticated}
				<button 
					type="button"
					class="px-1.5 py-0.5 text-[10px] font-medium rounded instant-tooltip tooltip-bottom {isQuotaExhausted ? 'bg-red-500/30 text-red-200' : 'bg-white/10 text-blue-100'}"
					data-tooltip="Messages used: {quotaUsed}/{quotaLimit}"
					on:click={toggleQuotaTooltip}
					bind:this={quotaElement}
				>
					{quotaUsed}/{quotaLimit}
				</button>
			{/if}
			{#if isPaidUser}
				<a
					href="/billing"
					class="px-2 py-1 bg-teal-400/20 text-teal-200 text-xs rounded font-medium"
				>
					Sub
				</a>
			{:else if isAuthenticated}
				<a
					href="/billing"
					class="px-2 py-1 text-blue-200 text-xs hover:text-white"
				>
					Subscribe
				</a>
			{:else}
				<button
					on:click={() => dispatch('openSignIn')}
					class="touch-target flex items-center justify-center p-2 rounded-lg hover:bg-blue-500/50 transition mobile-tap-highlight"
					aria-label="Sign in"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
					</svg>
				</button>
			{/if}
			<!-- Settings gear icon -->
			<button
				on:click={() => dispatch('openSettings')}
				class="touch-target flex items-center justify-center p-2 rounded-lg hover:bg-blue-500/50 transition mobile-tap-highlight"
				aria-label="Settings"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
				</svg>
			</button>
		</div>
	</div>

	<!-- Chat Actions Menu (dropdown) -->
	{#if showChatMenu}
		<!-- Backdrop -->
		<button
			class="fixed inset-0 z-40 bg-black/20"
			on:click={() => (showChatMenu = false)}
			aria-label="Close menu"
		></button>
		
		<!-- Menu -->
		<div class="absolute left-1/2 -translate-x-1/2 top-full mt-1 z-50 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1 min-w-[180px]">
			<!-- Response Modifier -->
			<button
				on:click={() => handleMenuAction(() => dispatch('toggleModifier'), true)}
				class="w-full px-4 py-3 text-left text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3"
			>
				{#if responseModifier === 'chat'}
					<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
					</svg>
				{:else if responseModifier === 'deep'}
					<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
					</svg>
				{:else}
					<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
					</svg>
				{/if}
				<span>Modifier: <span class="font-medium">{responseModifier === 'chat' ? 'Chat' : responseModifier === 'deep' ? 'Deep' : 'Off'}</span></span>
			</button>
			
			<div class="border-t border-gray-200 dark:border-gray-700 my-1"></div>
			
			<!-- Export -->
			<button
				on:click={() => handleMenuAction(() => dispatch('exportChat'))}
				disabled={messageCount === 0}
				class="w-full px-4 py-3 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3 {messageCount === 0 ? 'text-gray-400 dark:text-gray-500' : 'text-gray-700 dark:text-gray-200'}"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
				</svg>
				<span>Export Chat</span>
			</button>
			
			<!-- Clear -->
			<button
				on:click={() => handleMenuAction(() => dispatch('clearChat'))}
				disabled={messageCount === 0}
				class="w-full px-4 py-3 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3 {messageCount === 0 ? 'text-gray-400 dark:text-gray-500' : 'text-gray-700 dark:text-gray-200'}"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
				</svg>
				<span>Clear Chat</span>
			</button>
			
			<!-- Summarize -->
			<button
				on:click={() => handleMenuAction(() => dispatch('summarizeChat'))}
				disabled={messageCount === 0}
				class="w-full px-4 py-3 text-left text-sm hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-3 {messageCount === 0 ? 'text-gray-400 dark:text-gray-500' : 'text-gray-700 dark:text-gray-200'}"
			>
				<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
				</svg>
				<span>Summarize Chat</span>
			</button>
		</div>
	{/if}
</header>
