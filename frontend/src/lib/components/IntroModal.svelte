<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let isOpen = false;

	const dispatch = createEventDispatcher<{ ok: void; dismiss: void }>();

	function handleOk() {
		dispatch('ok');
	}

	function handleDismiss() {
		dispatch('dismiss');
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			handleOk(); // Clicking backdrop = OK (will show again)
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			handleOk();
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
	<!-- Modal Backdrop -->
	<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-noninteractive-element-interactions -->
	<div
		class="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
		on:click={handleBackdropClick}
		role="dialog"
		aria-modal="true"
		aria-labelledby="intro-title"
		tabindex="-1"
	>
		<!-- Modal Content -->
		<div class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
			<!-- Header -->
			<div class="px-6 py-5 border-b border-gray-200 dark:border-gray-700 text-center">
				<h2 id="intro-title" class="text-2xl font-bold text-gray-900 dark:text-white">
					👋 Welcome to botchat!
				</h2>
				<p class="text-gray-600 dark:text-gray-400 mt-1">Your privacy-first AI chat companion</p>
			</div>

			<!-- Scrollable Content -->
			<div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
				
				<!-- EDIT THIS SECTION: Core concept -->
				<section>
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
						<span class="text-xl">🤖</span> What makes botchat different?
					</h3>
					<p class="text-gray-700 dark:text-gray-300 leading-relaxed">
						Chat with <strong>multiple AI bots at once</strong>. Ask a question and get perspectives from 
						OpenAI, Claude, and Gemini powered bots, side-by-side. Compare responses, find the best answers, or see how 
						different AI personalities approach your problem.
					</p>
				</section>

				<!-- EDIT THIS SECTION: Getting started steps -->
				<section>
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
						<span class="text-xl">🚀</span> Getting started
					</h3>
					<ol class="space-y-3 text-gray-700 dark:text-gray-300">
						<li class="flex gap-3">
							<span class="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded-full flex items-center justify-center text-sm font-semibold">1</span>
							<span><strong>Create bots</strong> — Use the Bot Library to create AI assistants with custom personalities and instructions.</span>
						</li>
						<li class="flex gap-3">
							<span class="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded-full flex items-center justify-center text-sm font-semibold">2</span>
							<span><strong>Add bots to your chat</strong> — Click on the + button to add saved bots to your current chat. Add multiple for parallel responses!</span>
						</li>
						<li class="flex gap-3">
							<span class="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded-full flex items-center justify-center text-sm font-semibold">3</span>
							<span><strong>Start chatting!</strong> — Type your message and all active bots will respond simultaneously.</span>
						</li>
					</ol>
				</section>

				<!-- EDIT THIS SECTION: Privacy highlight -->
				<section class="bg-green-50 dark:bg-green-900/20 rounded-lg p-4 border border-green-200 dark:border-green-800">
					<h3 class="text-lg font-semibold text-green-800 dark:text-green-300 mb-2 flex items-center gap-2">
						<span class="text-xl">🔒</span> Privacy first
					</h3>
					<ul class="text-green-700 dark:text-green-400 space-y-1 text-sm">
						<li>• Your conversations are stored only in your browser</li>
						<li>• No server-side logging of your chats</li>
						<li>• When using botchat with built-in API keys, your data is never retained or used for model training</li>
						<li>• If using your own API keys, they are encrypted and stored only in your browser</li>
					</ul>
				</section>

				<!-- EDIT THIS SECTION: Tips -->
				<section>
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
						<span class="text-xl">💡</span> Pro tips
					</h3>
					<ul class="text-gray-700 dark:text-gray-300 space-y-2 text-sm">
						<li>• <strong>Response mode modifiers:</strong> Toggle between Chat (brief) and Deep (comprehensive) modes using the built-in chat</li>
						<li>• <strong>Attachments:</strong> Upload PDFs, images, or text files for AI analysis</li>
						<li>• <strong>Keyboard shortcut:</strong> Press <kbd class="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs">S</kbd> to toggle the sidebar</li>
					</ul>
				</section>

			</div>

			<!-- Footer with buttons -->
			<div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row gap-3 sm:justify-end">
				<button
					on:click={handleDismiss}
					class="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition text-sm"
				>
					Don't show again
				</button>
				<button
					on:click={handleOk}
					class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition"
				>
					Got it!
				</button>
			</div>
		</div>
	</div>
{/if}
