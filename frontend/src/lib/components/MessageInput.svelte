<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let isLoading = false;
	export let botsCount = 0;
	export let onCancel: (() => void) | null = null;
	export let messages: Array<{ content: string; role: string }> = [];
	export let activeBots: Array<{ name?: string; systemInstructionText?: string }> = [];
	export let globalAttachments: File[] = [];
	export let currentMessage = ''; // Bound to parent for token estimation
	export let hasOversizedAttachments = false; // Block sending if true

	const dispatch = createEventDispatcher<{ send: string }>();

	let inputElement: HTMLTextAreaElement;
	let estimatedTokens = 0;

	function estimateTokens(inputText: string): number {
		// Rough token estimation: ~4 characters per token (industry standard)
		// This estimates INPUT tokens only - the context window being sent to the LLM
		
		let totalText = '';

		// Add average system instruction length (varies slightly per bot)
		let avgSystemInstructionLength = 0;
		if (activeBots.length > 0) {
			const totalSysLength = activeBots.reduce((sum, bot) => sum + (bot.systemInstructionText?.length || 0), 0);
			avgSystemInstructionLength = totalSysLength / activeBots.length;
		}

		// Add conversation history
		for (const msg of messages) {
			totalText += msg.content + ' ';
		}

		// Add attachment tokens (estimate ~1 token per 4000 bytes, plus base tokens per file)
		let attachmentTokens = 0;
		for (const file of globalAttachments) {
			const fileTokens = Math.ceil(file.size / 4000) + 50; // 50 base tokens per file
			attachmentTokens += fileTokens;
		}

		// Add the current message
		totalText += inputText;

		// Input tokens only = system instruction + conversation history + message + attachments
		return Math.ceil(avgSystemInstructionLength / 4) + Math.ceil(totalText.length / 4) + attachmentTokens;
	}

	function handleSendOrCancel() {
		if (isLoading && onCancel) {
			onCancel();
		} else if (currentMessage.trim() && botsCount > 0 && !hasOversizedAttachments) {
			dispatch('send', currentMessage);
			currentMessage = '';
			estimatedTokens = 0;
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
		// Update token estimate as user types
		estimatedTokens = estimateTokens(currentMessage);
	}

	// Reactive statement to update token estimate when message, bots, or attachments change
	$: if (currentMessage || activeBots.length > 0 || globalAttachments.length > 0) {
		estimatedTokens = estimateTokens(currentMessage);
	}

	// Set initial height on mount for mobile
	import { onMount } from 'svelte';
	onMount(() => {
		autoResize();
	});
</script>

<div class="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-2 md:p-3 md:rounded-b-lg">
	<div class="flex items-start border border-gray-300 dark:border-gray-600 rounded-xl md:rounded-lg focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 overflow-hidden bg-gray-50 dark:bg-gray-700">
		<textarea
			bind:this={inputElement}
			bind:value={currentMessage}
			on:input={autoResize}
			on:keydown={handleKeydown}
			disabled={isLoading || botsCount === 0}
			placeholder={botsCount === 0 ? 'Add bots first...' : 'Type a message...'}
			rows="1"
			class="flex-1 px-3 md:px-4 py-2.5 md:py-2 border-0 resize-none focus:outline-none focus:ring-0 disabled:bg-gray-100 dark:disabled:bg-gray-700 disabled:cursor-not-allowed text-base md:text-sm bg-transparent dark:text-white dark:placeholder-gray-400"
		></textarea>
		<div class="flex items-center pl-2 md:pl-3 gap-2">
			<!-- Token count (hidden on mobile to save space) -->
			{#if currentMessage.trim() && estimatedTokens > 0}
				<div class="hidden md:block text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
					~{estimatedTokens.toLocaleString()}
				</div>
			{/if}
			<!-- Send/Cancel button -->
			<button
				on:click={handleSendOrCancel}
				disabled={isLoading ? false : !currentMessage.trim() || botsCount === 0 || hasOversizedAttachments}
				title={hasOversizedAttachments ? 'Remove oversized attachments (>50MB) to send' : ''}
				class="touch-target flex items-center justify-center min-w-[44px] h-[44px] md:min-w-0 md:h-auto md:px-5 md:py-2 rounded-l-lg md:rounded-l-lg rounded-r-none font-medium text-sm transition whitespace-nowrap mobile-tap-highlight {isLoading
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
</div>