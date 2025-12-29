<script lang="ts">
	import { onMount } from 'svelte';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';

	interface Bot {
		id: string;
		name?: string;
		provider: string;
		model: string;
	}

	export let isOpen = false;
	export let summaryContent = '';
	export let botName = '';
	export let botProvider = '';
	export let botModel = '';
	export let messageCount = 0;
	export let timestamp = new Date();
	export let conversationName = '';
	export let conversationDescription = '';
	export let participatingBots: Bot[] = [];

	let contentElement: HTMLDivElement;
	let renderedHtml = '';

	$: if (summaryContent) {
		// Build participating bots section
		let botsSection = '';
		if (participatingBots.length > 0) {
			botsSection = `

**Bots Participated (${participatingBots.length}):**
${participatingBots.map(b => `- ${b.name || 'Unnamed'} (${b.provider} / ${b.model})`).join('\n')}`;
		}

		// Render markdown to HTML
		const metadata = `**Chat:** ${conversationName}  
${conversationDescription ? `**Description:** ${conversationDescription}  ` : ''}**Generated:** ${timestamp.toLocaleString()}  
**Summarized by:** ${botName || `${botProvider} - ${botModel}`}  
**Messages Summarized:** ${messageCount}${botsSection}`;

		const markdown = `# Chat Summary

${metadata}

---

${summaryContent}`;
		
		renderedHtml = DOMPurify.sanitize(marked.parse(markdown) as string);
	}

	function handleClose() {
		document.dispatchEvent(new CustomEvent('closeSummaryModal'));
	}

	function handleSave() {
		let botsSection = '';
		if (participatingBots.length > 0) {
			botsSection = `

Bots Participated (${participatingBots.length}):
${participatingBots.map(b => `- ${b.name || 'Unnamed'} (${b.provider} / ${b.model})`).join('\n')}`;
		}

		const metadata = `Chat: ${conversationName}
${conversationDescription ? `Description: ${conversationDescription}
` : ''}Generated: ${timestamp.toLocaleString()}
Summarized by: ${botName || `${botProvider} - ${botModel}`}
Messages Summarized: ${messageCount}${botsSection}`;

		const fileContent = `# botchat | many minds, no memory

# Chat Summary

${metadata}

---

${summaryContent}`;

		const blob = new Blob([fileContent], { type: 'text/markdown' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `summary-${Date.now()}.md`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}

	function handleCopy() {
		let botsSection = '';
		if (participatingBots.length > 0) {
			botsSection = `

Bots Participated (${participatingBots.length}):
${participatingBots.map(b => `- ${b.name || 'Unnamed'} (${b.provider} / ${b.model})`).join('\n')}`;
		}

		const metadata = `Chat: ${conversationName}
${conversationDescription ? `Description: ${conversationDescription}
` : ''}Generated: ${timestamp.toLocaleString()}
Summarized by: ${botName || `${botProvider} - ${botModel}`}
Messages Summarized: ${messageCount}${botsSection}`;

		const fileContent = `# botchat | many minds, no memory

# Chat Summary

${metadata}

---

${summaryContent}`;

		navigator.clipboard.writeText(fileContent).then(() => {
			// Show feedback
			const button = event?.target as HTMLButtonElement;
			if (button) {
				const originalText = button.textContent;
				button.textContent = '✓ Copied!';
				setTimeout(() => {
					button.textContent = originalText;
				}, 2000);
			}
		});
	}

	function handlePrint() {
		// Reuse the rendered HTML for a print-friendly view
		const printWindow = window.open('', '_blank');
		if (!printWindow) return;

		// Add app header to the HTML
		const headerHtml = '<h1>botchat | many minds, no memory</h1>';
		const fullHtml = headerHtml + renderedHtml;

		printWindow.document.write(`
			<!DOCTYPE html>
			<html>
			<head>
				<title>Summary</title>
				<style>
					body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }
					h1 { color: #1a1a1a; border-bottom: 2px solid #3b82f6; padding-bottom: 10px; }
					h2 { color: #374151; margin-top: 30px; }
					h3 { color: #4b5563; margin-top: 20px; }
					p { margin: 10px 0; }
					li { margin-left: 20px; }
					@media print { body { padding: 0; } }
				</style>
			</head>
			<body>${fullHtml}</body>
			</html>
		`);
		printWindow.document.close();
		printWindow.print();
	}

	onMount(() => {
		function handleKeyDown(e: KeyboardEvent) {
			if (e.key === 'Escape' && isOpen) {
				handleClose();
			}
		}

		window.addEventListener('keydown', handleKeyDown);
		return () => window.removeEventListener('keydown', handleKeyDown);
	});
</script>

{#if isOpen}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col">
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<button
					on:click={handleClose}
					class="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition"
					title="Close (Esc)"
				>
					<svg class="w-6 h-6 text-gray-600 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Content -->
			<div
				bind:this={contentElement}
				class="flex-1 overflow-y-auto px-6 py-4 prose prose-sm max-w-none dark:prose-invert prose-p:my-2 prose-headings:mt-4 prose-headings:mb-2 prose-h1:text-lg prose-h2:text-base prose-h3:text-sm prose-ul:my-2 prose-ul:pl-4 prose-li:my-1 prose-ol:my-2 prose-ol:pl-4 prose-blockquote:border-l-4 prose-blockquote:border-gray-400 dark:prose-blockquote:border-gray-500 prose-blockquote:pl-3 prose-blockquote:italic prose-blockquote:my-2 prose-code:bg-gray-200 dark:prose-code:bg-gray-700 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-pre:p-3 prose-pre:rounded prose-pre:my-2 prose-pre:overflow-x-auto prose-a:text-blue-600 dark:prose-a:text-blue-400 prose-a:underline hover:prose-a:text-blue-800 dark:hover:prose-a:text-blue-300 prose-strong:font-bold prose-em:italic"
			>
				{@html renderedHtml}
			</div>

			<!-- Footer -->
			<div class="flex flex-wrap items-center justify-center gap-2 px-4 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 rounded-b-lg">
				<button
					on:click={handleClose}
					class="flex-1 min-w-[70px] max-w-[120px] px-3 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition font-medium text-sm"
				>
					Close
				</button>
				<button
					on:click={handleCopy}
					class="flex-1 min-w-[70px] max-w-[120px] px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium text-sm flex items-center justify-center gap-1.5"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
					</svg>
					Copy
				</button>
				<button
					on:click={handlePrint}
					class="flex-1 min-w-[70px] max-w-[120px] px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition font-medium text-sm flex items-center justify-center gap-1.5"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 9V4h12v5M6 18h12v2H6zM6 14h12v4H6zM6 9h12v5H6z" />
					</svg>
					Print
				</button>
				<button
					on:click={handleSave}
					class="flex-1 min-w-[70px] max-w-[120px] px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition font-medium text-sm flex items-center justify-center gap-1.5"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
					</svg>
					Save
				</button>
			</div>
		</div>
	</div>
{/if}
