<script lang="ts">
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import CitationsPopup from './CitationsPopup.svelte';
	import type { Citation } from './CitationsPopup.svelte';

	interface Message {
		id: string;
		role: 'user' | 'assistant';
		content: string;
		timestamp: number;
		botId?: string;
		provider?: string;
		model?: string;
		isError?: boolean;
		isTruncated?: boolean; // Response was cut off due to max_tokens limit
		finishReason?: string; // Raw finish_reason from provider
		citations?: Citation[]; // Web search citations
		lastInputs?: {
			message: string;
			attachments: File[];
		};
	}

	interface Bot {
		id: string;
		provider: string;
		model: string;
		name?: string;
		webSearchEnabled?: boolean;
	}

	export let messages: Message[] = [];
	export let activeBots: Bot[] = [];
	export let pendingBots: Set<string> = new Set(); // Bots waiting for first token (show loading spinner)
	export let onRetry: ((msg: Message) => void) | null = null;

	let messagesContainer: HTMLDivElement;
	let showCitationsPopup = false;
	let selectedCitations: Citation[] = [];

	// Configure marked for better rendering with custom link renderer
	// Custom renderer to make all links open in a new tab
	const renderer = new marked.Renderer();
	const originalLinkRenderer = renderer.link;
	renderer.link = function(href: string, title: string | null, text: string) {
		const html = originalLinkRenderer.call(this, href, title, text);
		// Add target="_blank" and rel="noopener noreferrer" for security
		return html.replace('<a ', '<a target="_blank" rel="noopener noreferrer" ');
	};

	marked.setOptions({
		breaks: true,
		gfm: true,
		renderer: renderer
	});

	// Configure DOMPurify to allow target attribute on links (for opening in new tabs)
	// By default DOMPurify strips target="_blank" for security, but we explicitly add it
	DOMPurify.addHook('afterSanitizeAttributes', function(node) {
		// Set all links to open in new tab
		if (node.tagName === 'A') {
			node.setAttribute('target', '_blank');
			node.setAttribute('rel', 'noopener noreferrer');
		}
	});

	function scrollToBottom() {
		if (messagesContainer) {
			setTimeout(() => {
				messagesContainer.scrollTop = messagesContainer.scrollHeight;
			}, 0);
		}
	}

	// Track previous message count to detect new messages
	let previousMessageCount = 0;

	$: {
		// Only auto-scroll if a NEW message was added (not just updated)
		// This allows users to scroll up while tokens are streaming
		if (messages.length > previousMessageCount) {
			scrollToBottom();
			previousMessageCount = messages.length;
		} else {
			previousMessageCount = messages.length;
		}
	}

	function getBotName(botId?: string): string | null {
		if (!botId) return null;
		const bot = activeBots.find((b) => b.id === botId);
		return bot?.name || null;
	}

	function getBotLabel(botId?: string): string {
		if (!botId) return 'Assistant';
		const bot = activeBots.find((b) => b.id === botId);
		return bot ? `${bot.provider} • ${bot.model}` : 'Unknown';
	}

	function openCitations(citations: Citation[]) {
		selectedCitations = citations;
		showCitationsPopup = true;
	}

	function closeCitations() {
		showCitationsPopup = false;
		selectedCitations = [];
	}

	/**
	 * Render markdown content and sanitize HTML output to prevent XSS attacks.
	 * DOMPurify removes any potentially malicious scripts/attributes.
	 */
	function renderMarkdown(content: string): Promise<string> {
		const rawHtml = marked.parse(content);
		return Promise.resolve(DOMPurify.sanitize(rawHtml as string));
	}

	$: {
		// Only auto-scroll if a NEW message was added (not just updated)
		// This allows users to scroll up while tokens are streaming
		if (messages.length > previousMessageCount) {
			scrollToBottom();
			previousMessageCount = messages.length;
		} else {
			previousMessageCount = messages.length;
		}
	}
</script>

<div bind:this={messagesContainer} class="flex-1 overflow-y-auto p-3 md:p-4 space-y-3 md:space-y-4 mobile-scroll">
	{#if messages.length === 0}
		<div class="h-full flex items-center justify-center text-center px-4">
			<div>
				<svg class="w-12 h-12 mx-auto mb-3 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
				</svg>
				<p class="text-gray-500 dark:text-gray-400 text-base md:text-lg font-medium">No messages yet</p>
				<p class="text-gray-400 dark:text-gray-500 text-sm mt-1">Select bots and send a message to get started</p>
			</div>
		</div>
	{/if}
	
	{#each messages as msg (msg.id)}
		<div class={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
			<div class="relative max-w-[90%] md:max-w-2xl">
				<div
					class={`px-3 md:px-4 py-2.5 md:py-3 rounded-2xl md:rounded-lg ${
						msg.role === 'user'
							? 'bg-blue-600 text-white rounded-br-sm md:rounded-br-none'
							: msg.content.startsWith('❌')
								? 'bg-red-50 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-bl-sm md:rounded-bl-none text-red-900 dark:text-red-100'
								: 'bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-bl-sm md:rounded-bl-none text-gray-900 dark:text-gray-100'
					}`}
				>
					{#if msg.role === 'assistant'}
						{#if getBotName(msg.botId)}
							<div class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-0.5">{getBotName(msg.botId)}</div>
						{/if}
						<div class="text-[10px] md:text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5 md:mb-2">{getBotLabel(msg.botId)}</div>
						<div class="prose prose-sm max-w-none dark:prose-invert text-sm leading-relaxed prose-p:m-0 prose-p:mb-2 prose-headings:mt-3 prose-headings:mb-2 prose-h1:text-base prose-h2:text-sm prose-h3:text-sm prose-ul:m-0 prose-ul:mb-2 prose-ul:pl-4 prose-li:m-0 prose-ol:m-0 prose-ol:mb-2 prose-ol:pl-4 prose-blockquote:border-l-4 prose-blockquote:border-gray-400 dark:prose-blockquote:border-gray-500 prose-blockquote:pl-3 prose-blockquote:italic prose-blockquote:m-0 prose-blockquote:mb-2 prose-code:bg-gray-200 dark:prose-code:bg-gray-700 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-red-600 dark:prose-code:text-red-400 prose-code:text-xs prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:p-3 prose-pre:rounded prose-pre:mb-2 prose-pre:overflow-x-auto prose-a:text-blue-600 dark:prose-a:text-blue-400 prose-a:underline hover:prose-a:text-blue-800 dark:hover:prose-a:text-blue-300 prose-strong:font-bold prose-em:italic">
							{#await renderMarkdown(msg.content)}
								<p>Loading...</p>
							{:then html}
								{@html html}
							{:catch}
								<p>{msg.content}</p>
							{/await}
						</div>
						{#if msg.isTruncated}
							<div class="mt-2 pt-2 border-t border-amber-300 dark:border-amber-600">
								<div class="flex items-center gap-1.5 text-xs text-amber-700 dark:text-amber-400">
									<svg class="w-4 h-4 text-amber-500 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
									</svg>
									<span class="font-medium">Response truncated</span>
									<span class="text-amber-600 dark:text-amber-500">— max_tokens limit reached. Increase in bot settings for longer responses.</span>
								</div>
							</div>
						{/if}
						{#if msg.citations && msg.citations.length > 0}
							<div class="mt-2 pt-2 border-t border-blue-200 dark:border-blue-800">
								<button
									on:click={() => openCitations(msg.citations || [])}
									class="flex items-center gap-1.5 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition font-medium"
								>
									<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
									</svg>
									<span>View {msg.citations.length} web source{msg.citations.length === 1 ? '' : 's'}</span>
									<svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
									</svg>
								</button>
							</div>
						{/if}
					{:else}
						<p class="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
					{/if}
				</div>
				
				{#if msg.role === 'assistant' && msg.isError && onRetry}
					<div class="absolute -top-2 -right-2">
						<button
							class="w-5 h-5 rounded-full bg-amber-500 hover:bg-amber-600 flex items-center justify-center text-sm shadow-lg hover:shadow-xl transition-all cursor-pointer text-white text-xs leading-none pb-0.5"
							on:click={() => onRetry?.(msg)}
							title="Retry this message"
						>
							↻
						</button>
					</div>
				{/if}
			</div>
		</div>
	{/each}
	
	<!-- Loading spinners for pending bots (waiting for first token) -->
	{#each activeBots.filter(b => pendingBots.has(b.id)) as bot (bot.id)}
		<div class="flex justify-start">
			<div class="max-w-[80%] p-3 rounded-2xl bg-gray-100 dark:bg-gray-700 rounded-bl-md">
				<div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 mb-2">
					<span class="font-medium">{bot.name || bot.model}</span>
					<span>•</span>
					<span class="capitalize">{bot.provider}</span>
					{#if bot.webSearchEnabled}
						<span title="Web search enabled">
							<svg class="w-3.5 h-3.5 text-blue-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5a17.919 17.919 0 01-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
							</svg>
						</span>
					{/if}
				</div>
				<div class="flex items-center gap-2 text-gray-500 dark:text-gray-400">
					<!-- Animated loading dots -->
					<div class="flex items-center gap-1">
						<span class="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style="animation-delay: 0ms;"></span>
						<span class="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style="animation-delay: 150ms;"></span>
						<span class="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style="animation-delay: 300ms;"></span>
					</div>
					<span class="text-sm">{bot.webSearchEnabled ? 'Searching & thinking...' : 'Thinking...'}</span>
				</div>
			</div>
		</div>
	{/each}
</div>

<!-- Citations Popup -->
<CitationsPopup 
	citations={selectedCitations} 
	isOpen={showCitationsPopup} 
	on:close={closeCitations}
/>

<style>
	/* Ensure tooltip text breaks properly */
	:global(.prose) {
		overflow-wrap: break-word;
		word-break: break-word;
	}
</style>
