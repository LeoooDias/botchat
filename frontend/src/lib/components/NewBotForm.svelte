<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { getMaxOutput } from '$lib/modelLimits';
	import { getUserItem } from '$lib/utils/userStorage';
	import PersonaWizard from './PersonaWizard.svelte';

	interface Bot {
		id: string;
		provider: string;
		model: string;
		systemInstructionFile?: File;
		systemInstructionText?: string;
		name?: string;
		maxTokens?: number;
		category?: string;
		webSearchEnabled?: boolean;
	}

	interface Category {
		id: string;
		name: string;
	}

	const dispatch = createEventDispatcher<{ save: Bot; openSettings: void }>();

	// All available providers with their models
	// Platform keys are now the default - all providers always available
	const providers = [
		{ name: 'Anthropic', value: 'anthropic', models: ['claude-sonnet-4-5', 'claude-haiku-4-5', 'claude-opus-4-5'] },
		{ name: 'Google', value: 'gemini', models: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.5-flash-lite'] },
		{ name: 'OpenAI', value: 'openai', models: ['gpt-5.2', 'gpt-5', 'gpt-5-nano','gpt-4.1', 'gpt-5-mini'] }
	];

	let selectedProvider = '';
	let selectedModel = '';
	let botName = '';
	let maxTokens: number | undefined = undefined;
	let systemInstructionFile: File | null = null;
	let webSearchEnabled = false;

	// Reactive validation for maxTokens
	const MIN_TOKENS = 100;
	$: modelMaxOutput = selectedProvider && selectedModel ? getMaxOutput(selectedProvider, selectedModel) : undefined;
	$: maxTokensError = (() => {
		if (!maxTokens) return ''; // Empty is valid (will use default)
		if (maxTokens < MIN_TOKENS) return `Minimum is ${MIN_TOKENS} tokens`;
		if (modelMaxOutput && maxTokens > modelMaxOutput) return `Exceeds model limit of ${modelMaxOutput.toLocaleString()} tokens`;
		return '';
	})();
	$: isMaxTokensValid = !maxTokensError;
	let systemInstructionText = '';
	let selectedCategory = '';
	let categories: Category[] = [];
	let showPersonaWizard = false;

	onMount(() => {
		// Load categories from user-namespaced storage
		loadCategories();
		
		// Listen for storage changes to update categories when they're modified in BotLibrary
		window.addEventListener('storage', handleStorageChange);
		
		// Also set up a custom event listener for same-window updates
		window.addEventListener('categoriesUpdated', loadCategories);
		
		return () => {
			window.removeEventListener('storage', handleStorageChange);
			window.removeEventListener('categoriesUpdated', loadCategories);
		};
	});

	function handleStorageChange(e: StorageEvent) {
		if (e.key === 'botCategories') {
			loadCategories();
		}
	}

	function loadCategories() {
		const storedCategories = getUserItem('botCategories');
		if (storedCategories) {
			try {
				categories = JSON.parse(storedCategories);
			} catch (e) {
				console.error('Failed to load categories:', e);
				categories = [];
			}
		} else {
			categories = [];
		}
	}

	function handleFileUpload(e: Event) {
		const input = e.target as HTMLInputElement;
		systemInstructionFile = input.files?.[0] || null;
	}

	function clearFile() {
		systemInstructionFile = null;
		// Reset the file input
		const fileInput = document.getElementById('system-file') as HTMLInputElement;
		if (fileInput) fileInput.value = '';
	}

	function saveAndAdd() {
		if (!selectedProvider || !selectedModel || !isMaxTokensValid) return;

		const bot: Bot = {
			id: crypto.randomUUID(),
			provider: selectedProvider,
			model: selectedModel,
			systemInstructionFile: systemInstructionFile || undefined,
			systemInstructionText: systemInstructionText || undefined,
			name: botName || undefined,
			maxTokens: maxTokens || undefined,
			category: selectedCategory || undefined,
			webSearchEnabled: webSearchEnabled || undefined
		};

		dispatch('save', bot);

		// Reset form
		selectedProvider = '';
		selectedModel = '';
		botName = '';
		maxTokens = undefined;
		systemInstructionFile = null;
		systemInstructionText = '';
		selectedCategory = '';
		webSearchEnabled = false;
	}

	$: availableModels = providers.find((p) => p.value === selectedProvider)?.models || [];
	
	// Reactively reload categories when user storage might have changed
	$: if (typeof window !== 'undefined') {
		// This runs periodically to catch category updates
		const checkCategories = () => {
			const stored = getUserItem('botCategories');
			const current = JSON.stringify(categories);
			if (stored !== current) {
				loadCategories();
			}
		};
		// Check on each reactive update
		checkCategories();
	}
	
	// Export function to allow parent to trigger category reload
	export function refreshCategories() {
		loadCategories();
	}

	function handlePersonaGenerated(event: CustomEvent<{ name: string; instruction: string }>) {
		const { name, instruction } = event.detail;
		botName = name;
		systemInstructionText = instruction;
		showPersonaWizard = false;
	}
</script>

<div>
	<div class="space-y-3">
		<!-- Provider -->
		<div>
			<label for="provider" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Provider</label>
			<select
				id="provider"
				bind:value={selectedProvider}
				class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
			>
				<option value="">Select provider...</option>
				{#each providers as p}
					<option value={p.value}>{p.name}</option>
				{/each}
			</select>
		</div>

		<!-- Model -->
		<div>
			<label for="model" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Model</label>
			<select
				id="model"
				bind:value={selectedModel}
				disabled={!selectedProvider}
				class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-600 dark:bg-gray-700 dark:text-white"
			>
				<option value="">Select model...</option>
				{#each availableModels as m}
					<option value={m}>{m}</option>
				{/each}
			</select>
		</div>

		<!-- System Instruction File -->
		<div>
			<div class="flex items-center gap-1 mb-1">
				<label for="system-file" class="block text-xs font-medium text-gray-700 dark:text-gray-300">Bot Instruction (optional)</label>
				<div class="relative group">
					<button
						type="button"
						class="w-4 h-4 rounded-full bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300 text-xs flex items-center justify-center hover:bg-gray-300 dark:hover:bg-gray-500 transition cursor-help"
						tabindex="-1"
					>?</button>
					<div class="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-72 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
						<p class="font-semibold mb-1">Example:</p>
						<p class="text-gray-200 leading-relaxed">You are a highly respected CFO with a track record of scaling high-growth companies from early-stage chaos through IPO. When answering, focus on: financial clarity, leading indicators, resource allocation, controls, and building repeatable systems that survive scale.</p>
						<div class="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-8 border-r-8 border-t-8 border-transparent border-t-gray-900"></div>
					</div>
				</div>
				<!-- Persona Wizard Button -->
				<button
					type="button"
					on:click={() => showPersonaWizard = true}
					class="ml-auto flex items-center gap-1.5 px-2 py-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition"
					title="Use AI to create a persona"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z" />
					</svg>
					Wizard
				</button>
			</div>
			
			<!-- Text Area -->
			<textarea
				id="system-text"
				bind:value={systemInstructionText}
				placeholder="Enter bot instruction..."
				rows="3"
				class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 resize-y mb-2 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400"
			></textarea>
			
			<!-- File Upload -->
			<div class="flex items-center gap-2">
				<span class="text-xs text-gray-500 dark:text-gray-400">Or upload file:</span>
				<input
					id="system-file"
					type="file"
					accept=".txt,.pdf,.docx,.md"
					on:change={handleFileUpload}
					class="block flex-1 text-xs text-gray-500 dark:text-gray-400 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-blue-50 dark:file:bg-blue-900/50 file:text-blue-700 dark:file:text-blue-300 hover:file:bg-blue-100 dark:hover:file:bg-blue-900"
				/>
			</div>
			{#if systemInstructionFile}
				<div class="flex items-center justify-between mt-1">
					<p class="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
						<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 12.75l6 6 9-13.5" />
						</svg>
						{systemInstructionFile.name}
					</p>
					<button
						type="button"
						on:click={clearFile}
						class="text-xs text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
					>Remove</button>
				</div>
				{#if systemInstructionText.trim()}
					<p class="text-xs text-amber-600 dark:text-amber-400 mt-1 flex items-center gap-1">
						<svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
						</svg>
						File attached - text above will be ignored
					</p>
				{/if}
			{/if}
		</div>

		<!-- Max Tokens -->
		<div>
			<label for="max-tokens" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Max Tokens (optional)</label>
			<input
				id="max-tokens"
				type="number"
				bind:value={maxTokens}
				disabled={!selectedModel}
				placeholder={!selectedModel ? 'Select a model first' : modelMaxOutput ? `100 – ${modelMaxOutput.toLocaleString()}` : 'Leave empty for default'}
				min={MIN_TOKENS}
				max={modelMaxOutput || undefined}
				class="w-full px-3 py-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 disabled:bg-gray-100 dark:disabled:bg-gray-600 disabled:cursor-not-allowed {maxTokensError ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500'}"
			/>
			{#if maxTokensError}
				<p class="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1">
					<svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
					</svg>
					{maxTokensError}
				</p>
			{:else if selectedModel}
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					Limits response length. Range: {MIN_TOKENS} – {modelMaxOutput?.toLocaleString() || 'unlimited'}
				</p>
			{:else}
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
					Select a model to see token limits
				</p>
			{/if}
		</div>

		<!-- Bot Name (for saving) -->
		<div>
			<label for="bot-name" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Bot Name (for library)</label>
			<input
				id="bot-name"
				type="text"
				placeholder="e.g., Chief Financial Officer"
				bind:value={botName}
				on:keydown={(e) => e.key === 'Enter' && saveAndAdd()}
				class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400"
			/>
		</div>

		<!-- Category -->
		<div>
			<label for="bot-category" class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">Category</label>
			<select
				id="bot-category"
				bind:value={selectedCategory}
				class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
			>
				<option value="">Uncategorized</option>
				{#each categories.filter(c => c.name.toLowerCase() !== 'uncategorized') as cat}
					<option value={cat.name}>{cat.name}</option>
				{/each}
			</select>
			<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
				Organize bots in collapsible categories. Create categories in the Bots section above.
			</p>
		</div>

		<!-- Web Search -->
		<div class="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
			<label class="relative inline-flex items-center cursor-pointer">
				<input
					type="checkbox"
					bind:checked={webSearchEnabled}
					class="sr-only peer"
				/>
				<div class="w-9 h-5 bg-gray-300 peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-blue-500 rounded-full peer dark:bg-gray-600 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-blue-600"></div>
			</label>
			<div class="flex-1">
				<div class="flex items-center gap-1.5">
					<span class="text-sm font-medium text-gray-700 dark:text-gray-300">Web Search</span>
					<svg class="w-4 h-4 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 008.716-6.747M12 21a9.004 9.004 0 01-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 017.843 4.582M12 3a8.997 8.997 0 00-7.843 4.582m15.686 0A11.953 11.953 0 0112 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0121 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0112 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 013 12c0-1.605.42-3.113 1.157-4.418" />
					</svg>
				</div>
				<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
					Allow this bot to search the web for current information. Citations will be shown.
				</p>
			</div>
		</div>

		<!-- Save & Add Button -->
		<button
			on:click={saveAndAdd}
			disabled={!selectedProvider || !selectedModel || !isMaxTokensValid}
			class="w-full px-4 py-3 md:py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition font-medium text-base md:text-sm"
		>
			Save & Add
		</button>
	</div>
</div>

<!-- Persona Wizard Modal -->
<PersonaWizard 
	isOpen={showPersonaWizard} 
	on:close={() => showPersonaWizard = false}
	on:generate={handlePersonaGenerated}
/>
