<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let isOpen = false;

	const dispatch = createEventDispatcher<{ close: void }>();

	function handleClose() {
		dispatch('close');
	}

	function handleBackdropClick(e: MouseEvent) {
		if (e.target === e.currentTarget) {
			handleClose();
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			handleClose();
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
		aria-labelledby="about-title"
		tabindex="-1"
	>
		<!-- Modal Content -->
		<div class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden">
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<h2 id="about-title" class="text-2xl font-bold text-gray-900 dark:text-white">About botchat</h2>
				<button
					on:click={handleClose}
					class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
					aria-label="Close"
				>
					<svg class="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Scrollable Content -->
			<div class="flex-1 overflow-y-auto px-6 py-6">
				<div class="prose dark:prose-invert max-w-none">
					<!-- ABOUT CONTENT START -->
					<!-- Edit this section to update the About page content -->
					
					<section class="mb-8">
						<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">What is botchat?</h3>
						<p class="text-gray-600 dark:text-gray-300 leading-relaxed">
							botchat is a privacy-preserving, multi-bot chat tool that lets you interact with multiple AI models simultaneously.
							Give bots personas, so they look at your question from multiple angles. Leverage the strengths of different models in the same chat. And most importantly, protect your data.</p><p>
							botchat never stores your conversations or attachments on any servers. And your data is never retained by the AI provider for model training.
						</p>
					</section>

					<section class="mb-8">
						<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-3">Key Features</h3>
						<ul class="list-disc list-inside text-gray-600 dark:text-gray-300 space-y-2">
							<li>Chat with multiple AI bots in a single conversation</li>
							<li>Support for OpenAI, Anthropic (Claude), and Google Gemini</li>
							<li>No AI provider data retention for model training.</li>							
							<li>Customizable personalities and instructions per bot</li>
							<li>File attachments and PDF support (your attachments never touch botchat servers)</li>
							<li>Privacy-by-design: botchat never stores chat or attachments on our servers</li>
							<li> BYOK: take full control by using your own API keys, stored safely in your browser</li>
							<li>Other than sending your prompts to AI providers, we don't share data with third parties</li>
						</ul>
					</section>

					<!-- FAQ SECTION -->
					<section class="mb-8">
						<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-4">Frequently Asked Questions</h3>
						
						<div class="space-y-4">
							<!-- FAQ Item Template -->
							<details class="group border border-gray-200 dark:border-gray-700 rounded-lg">
								<summary class="flex items-center justify-between cursor-pointer px-4 py-3 font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg">
									<span>Why does botchat exist?</span>
									<svg class="w-5 h-5 text-gray-500 group-open:rotate-180 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
									</svg>
								</summary>
								<div class="px-4 pb-4 text-gray-600 dark:text-gray-300">
									<p>botchat exists to make 2 things easier:</p>
									<ol class="list-decimal list-inside mt-2 space-y-1">
										<li>Analyzing something from multiple perspectives</li>
										<li>Keeping data private and confidential</li>
									</ol>
								</div>
							</details>
							
							<details class="group border border-gray-200 dark:border-gray-700 rounded-lg">
								<summary class="flex items-center justify-between cursor-pointer px-4 py-3 font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg">
									<span>How does it work?</span>
									<svg class="w-5 h-5 text-gray-500 group-open:rotate-180 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
									</svg>
								</summary>
								<div class="px-4 pb-4 text-gray-600 dark:text-gray-300">
									<p>botchat is a minimalist tool. It provides the minimal scaffolding to organize group chats with AI models. </p>
									<p>When you send a message, botchat forwards it to each bot's configured AI provider. No data is stored on botchat servers.</p>
									<p>It's widely known that AI providers (e.g., OpenAI, Google, Anthropic) offer more control over data retention and privacy through their APIs.</p> <p>botchat makes it easy to leverage the value of AI chatbots while keeping your information private.</p>
								</div>
							</details>

							<details class="group border border-gray-200 dark:border-gray-700 rounded-lg">
								<summary class="flex items-center justify-between cursor-pointer px-4 py-3 font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg">
									<span>Is my data private?</span>
									<svg class="w-5 h-5 text-gray-500 group-open:rotate-180 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
									</svg>
								</summary>
								<div class="px-4 pb-4 text-gray-600 dark:text-gray-300">
									<p>Yes. Your chats and attachments are never stored on our servers. Ever.</p>
									<p>Attachments are transmitted to AI providers through BytesIO streams, meaning they never touch disk in our servers.</p>
									<p>botchat ensures your chat and attachment data is not used for model training by AI providers. There is no "misconfiguration risk"</p>
									<p>If you're using your own API keys, they are encrypted with AES-256 and stored only in your browser's local storage.</p>
								</div>
							</details>

							<details class="group border border-gray-200 dark:border-gray-700 rounded-lg">
								<summary class="flex items-center justify-between cursor-pointer px-4 py-3 font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg">
									<span>What's the difference between free and paid plans?</span>
									<svg class="w-5 h-5 text-gray-500 group-open:rotate-180 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
									</svg>
								</summary>
								<div class="px-4 pb-4 text-gray-600 dark:text-gray-300">
									<p>When you first sign into botchat, you get 100 free messages.</p>
									<p>Free users can create up to 3 chats with 3 bots each.</p><p>Subscribers get unlimited chats and up to 10 bots per chat.</p>
								</div>
							</details>

							<details class="group border border-gray-200 dark:border-gray-700 rounded-lg">
								<summary class="flex items-center justify-between cursor-pointer px-4 py-3 font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg">
									<span>Why should I trust botchat?</span>
									<svg class="w-5 h-5 text-gray-500 group-open:rotate-180 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
									</svg>
								</summary>
								<div class="px-4 pb-4 text-gray-600 dark:text-gray-300">
									<p>You don't need to. botchat is fully open-source: </p><p><a href="https://github.com/LeoooDias/botchat" target="_blank" rel="noopener noreferrer" class="text-blue-600 dark:text-blue-400 hover:underline">https://github.com/LeoooDias/botchat</a> </p><p>I encourage you to review the code. Report issues. Request enhancements. Your contributions are welcome.</p>
								</div>
							</details>

							<details class="group border border-gray-200 dark:border-gray-700 rounded-lg">
								<summary class="flex items-center justify-between cursor-pointer px-4 py-3 font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg">
									<span>What am I paying for?</span>
									<svg class="w-5 h-5 text-gray-500 group-open:rotate-180 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
									</svg>
								</summary>
								<div class="px-4 pb-4 text-gray-600 dark:text-gray-300">
									<p>Simplicity, convenience, privacy, transparency, and hosting fees.</p>
								</div>
							</details>
							
							<details class="group border border-gray-200 dark:border-gray-700 rounded-lg">
								<summary class="flex items-center justify-between cursor-pointer px-4 py-3 font-medium text-gray-900 dark:text-white hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-lg">
									<span>How do I contact support?</span>
									<svg class="w-5 h-5 text-gray-500 group-open:rotate-180 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
									</svg>
								</summary>
								<div class="px-4 pb-4 text-gray-600 dark:text-gray-300">
									<p>Email me at <a href="mailto:leo@botchat.ca" class="text-blue-600 dark:text-blue-400 hover:underline">leo@botchat.ca</a> for any questions, feedback, feature requests, or support needs.</p>
								</div>
							</details>
						</div>
					</section>

					<!-- ABOUT CONTENT END -->
				</div>
			</div>

			<!-- Footer -->
			<div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
				<div class="flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
					<span>© 2025 botchat</span>
					<a href="mailto:leo@botchat.ca" class="hover:text-blue-600 dark:hover:text-blue-400">leo@botchat.ca</a>
				</div>
			</div>
		</div>
	</div>
{/if}
