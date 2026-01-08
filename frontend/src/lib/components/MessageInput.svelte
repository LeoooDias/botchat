<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let isLoading = false;
	export let botsCount = 0;
	export let onCancel: (() => void) | null = null;
	export let currentMessage = ''; // Bound to parent for token estimation
	export let hasOversizedAttachments = false; // Block sending if true
	export let hasInvalidActiveBots = false; // Block sending if any bot has invalid model

	const dispatch = createEventDispatcher<{ send: string }>();

	let inputElement: HTMLTextAreaElement;

	// Can send if: has message, has valid bots, no oversized attachments, no invalid bots
	$: canSend = currentMessage.trim() && botsCount > 0 && !hasOversizedAttachments && !hasInvalidActiveBots;

	function handleSendOrCancel() {
		if (isLoading && onCancel) {
			onCancel();
		} else if (canSend) {
			dispatch('send', currentMessage);
			currentMessage = '';
			// Reset textarea height after sending
			if (inputElement) {
				inputElement.style.height = 'auto';
			}
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSendOrCancel();
		}
	}

	function autoResize() {
		if (inputElement) {
			inputElement.style.height = 'auto';
			const scrollHeight = inputElement.scrollHeight;
			// Mobile: max 4 lines (~96px), expand to min 2 lines (~48px) only when content needs it
			// Desktop: max 5 lines (~120px)
			const isMobile = window.innerWidth < 768;
			const maxHeight = isMobile ? 96 : 120;
			// On mobile, if content overflows 1 line, jump to at least 2 lines for readability
			const minHeight = (isMobile && scrollHeight > 32) ? 48 : 0;
			inputElement.style.height = Math.max(minHeight, Math.min(scrollHeight, maxHeight)) + 'px';
		}
	}

	// Set initial height on mount for mobile
	import { onMount } from 'svelte';
	onMount(() => {
		autoResize();
	});
</script>

<div class="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-2 md:p-3 md:rounded-b-lg">
	<div class="flex items-end gap-2">
		<!-- Input area -->
		<div class="flex-1 flex items-start border border-gray-300 dark:border-gray-600 rounded-xl md:rounded-lg focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 overflow-hidden bg-gray-50 dark:bg-gray-700">
			<textarea
				bind:this={inputElement}
				bind:value={currentMessage}
				on:input={autoResize}
				on:keydown={handleKeydown}
				disabled={isLoading || botsCount === 0 || hasInvalidActiveBots}
				placeholder={botsCount === 0 ? 'Add bots first...' : (hasInvalidActiveBots ? 'Fix bot models to continue...' : 'Type a message...')}
				rows="1"
				class="flex-1 px-3 md:px-4 py-2.5 md:py-2 border-0 resize-none focus:outline-none focus:ring-0 disabled:bg-gray-100 dark:disabled:bg-gray-700 disabled:cursor-not-allowed text-base md:text-sm bg-transparent dark:text-white dark:placeholder-gray-400"
			></textarea>
		</div>
		<!-- Send/Cancel button - outside input container for better mobile UX -->
		<button
			on:click={handleSendOrCancel}
			disabled={isLoading ? false : !canSend}
			title={hasInvalidActiveBots ? 'Remove or fix bots with invalid models' : (hasOversizedAttachments ? 'Remove oversized attachments (>50MB) to send' : '')}
			class="flex-shrink-0 flex items-center justify-center w-11 h-11 md:w-auto md:h-auto md:px-5 md:py-2 rounded-full md:rounded-lg font-medium text-sm transition whitespace-nowrap {isLoading
				? 'bg-gray-200 dark:bg-gray-600 text-gray-900 dark:text-white hover:bg-gray-300 dark:hover:bg-gray-500'
				: 'bg-blue-600 text-white hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed'
			}"
		>
			{#if isLoading}
				<span class="hidden md:inline">Cancel</span>
				<svg class="w-5 h-5 md:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
			{:else}
				<span class="hidden md:inline">Send</span>
				<svg class="w-5 h-5 md:hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
				</svg>
			{/if}
		</button>
	</div>
</div>