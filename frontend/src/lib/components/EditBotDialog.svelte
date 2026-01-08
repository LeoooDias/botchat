<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { getMaxOutput, isBotModelValid, validateBotModel } from '$lib/modelLimits';

	interface Bot {
		id: string;
		provider: string;
		model: string;
		name?: string;
		systemInstructionText?: string;
		maxTokens?: number;
		category?: string;
	}

	export let bot: Bot | null = null;
	export let isOpen = false;

	const dispatch = createEventDispatcher<{ save: Bot; cancel: void }>();

	const providers = [
		{ name: 'Anthropic', value: 'anthropic', models: ['claude-sonnet-4-5', 'claude-haiku-4-5', 'claude-opus-4-5'] },
		{ name: 'Google', value: 'gemini', models: ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.5-flash-lite'] },
		{ name: 'OpenAI', value: 'openai', models: ['gpt-5.2', 'gpt-5', 'gpt-5-nano', 'gpt-4.1', 'gpt-5-mini'] }
	];

	let editedBot: Bot | null = null;
	let copiedInstruction = false;

	// Max tokens validation
	const MIN_TOKENS = 100;
	function getMaxTokensError(): string {
		if (!editedBot?.maxTokens) return ''; // Empty is valid (will use default)
		if (editedBot.maxTokens < MIN_TOKENS) return `Minimum is ${MIN_TOKENS} tokens`;
		const modelMax = getMaxOutput(editedBot.provider, editedBot.model);
		if (modelMax && editedBot.maxTokens > modelMax) {
			return `Exceeds model limit of ${modelMax.toLocaleString()} tokens`;
		}
		return '';
	}

	$: if (bot && isOpen) {
		editedBot = { ...bot };
		copiedInstruction = false;
	}

	$: botValid = editedBot ? isBotModelValid(editedBot) : true;
	$: validationError = editedBot ? validateBotModel(editedBot.provider, editedBot.model) : null;
	$: maxTokensError = getMaxTokensError();

	function handleSave() {
		if (editedBot && !maxTokensError) {
			dispatch('save', editedBot);
			close();
		}
	}

	function handleCancel() {
		dispatch('cancel');
		close();
	}

	function close() {
		isOpen = false;
		editedBot = null;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && isOpen) {
			handleCancel();
		} else if (event.altKey && event.code === 'KeyS' && isOpen && editedBot && !maxTokensError) {
			event.preventDefault();
			handleSave();
		}
	}

	function copyInstruction() {
		if (editedBot?.systemInstructionText) {
			navigator.clipboard.writeText(editedBot.systemInstructionText);
			copiedInstruction = true;
			setTimeout(() => { copiedInstruction = false; }, 2000);
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen && editedBot}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg w-full max-w-md max-h-[90vh] flex flex-col overflow-hidden">
			<!-- Header -->
			<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex-shrink-0">
				<h2 class="text-lg font-bold text-gray-900 dark:text-white">Edit Bot</h2>
			</div>

			<!-- Scrollable Content -->
			<div class="flex-1 overflow-y-auto px-6 py-4">
				<!-- Model validation warning -->
				{#if !botValid}
					<div class="mb-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-300 dark:border-red-700 rounded-lg">
						<div class="flex items-center gap-2 text-red-700 dark:text-red-300">
							<svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
							</svg>
							<span class="font-medium text-sm">Model no longer available</span>
						</div>
						<p class="mt-1 text-sm text-red-600 dark:text-red-400">
							Select a new model below to continue using this bot.
						</p>
					</div>
				{/if}

				<div class="space-y-4">
				<!-- Bot Name -->
				<div>
					<label for="edit-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						Name
					</label>
					<input
						id="edit-name"
						type="text"
						bind:value={editedBot.name}
						placeholder="e.g., Code Reviewer"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
						on:keydown={(e) => e.key === 'Enter' && !maxTokensError && handleSave()}
					/>
				</div>

				<!-- Provider & Model -->
				<div class="grid grid-cols-2 gap-3">
					<div>
						<label for="edit-provider" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Provider</label>
						<select
							id="edit-provider"
							bind:value={editedBot.provider}
							on:change={() => {
								// Reset model when provider changes
								const providerData = providers.find(p => p.value === editedBot?.provider);
								if (providerData && editedBot && !providerData.models.includes(editedBot.model)) {
									editedBot.model = providerData.models[0];
								}
							}}
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
						>
							{#each providers as provider}
								<option value={provider.value}>{provider.name}</option>
							{/each}
						</select>
					</div>
					<div>
						<label for="edit-model" class="block text-sm font-medium {!botValid ? 'text-red-600 dark:text-red-400' : 'text-gray-700 dark:text-gray-300'} mb-1">
							Model {#if !botValid}<span class="text-red-500">⚠</span>{/if}
						</label>
						<select
							id="edit-model"
							bind:value={editedBot.model}
							class="w-full px-3 py-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset dark:bg-gray-700 dark:text-white {!botValid ? 'border-red-400 dark:border-red-600 ring-2 ring-red-300 dark:ring-red-700 focus:ring-red-500' : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500'}"
						>
							{#each (providers.find(p => p.value === editedBot?.provider)?.models || []) as model}
								<option value={model}>{model}</option>
							{/each}
						</select>
					</div>
				</div>

				<!-- Bot Instruction -->
				<div>
					<div class="flex justify-between items-center mb-1">
						<label for="edit-system" class="text-sm font-medium text-gray-700 dark:text-gray-300">
							Bot Instruction (optional)
						</label>
						<button
							type="button"
							on:click={copyInstruction}
							class="p-1 {copiedInstruction ? 'text-green-500' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'} transition"
							title={copiedInstruction ? 'Copied!' : 'Copy to clipboard'}
						>
							{#if copiedInstruction}
								<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
									<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
								</svg>
							{:else}
								<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
									<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
									<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
								</svg>
							{/if}
						</button>
					</div>
					<textarea
						id="edit-system"
						bind:value={editedBot.systemInstructionText}
						placeholder="Enter bot instruction..."
						rows="4"
						class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 font-mono text-xs dark:bg-gray-700 dark:text-white dark:placeholder-gray-400"
					></textarea>
				</div>

				<!-- Max Tokens -->
				<div>
					<label for="edit-max-tokens" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						Max Tokens (optional)
					</label>
					<input
						id="edit-max-tokens"
						type="number"
						bind:value={editedBot.maxTokens}
						placeholder={getMaxOutput(editedBot.provider, editedBot.model) ? `${MIN_TOKENS} – ${getMaxOutput(editedBot.provider, editedBot.model)?.toLocaleString()}` : 'Leave empty for default'}
						min={MIN_TOKENS}
						max={getMaxOutput(editedBot.provider, editedBot.model) || undefined}
						class="w-full px-3 py-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 {maxTokensError ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500'}"
					/>
					{#if maxTokensError}
						<p class="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1">
							<svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
							</svg>
							{maxTokensError}
						</p>
					{:else}
						<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
							Range: {MIN_TOKENS} – {getMaxOutput(editedBot.provider, editedBot.model)?.toLocaleString() || 'unlimited'}
						</p>
					{/if}
				</div>
				</div>
			</div>

			<!-- Buttons -->
			<div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex gap-2 flex-shrink-0">
				<button
					on:click={handleCancel}
					class="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition font-medium text-sm"
				>
					Cancel
				</button>
				<button
					on:click={handleSave}
					disabled={!!maxTokensError}
					class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition font-medium text-sm"
				>
					Save Changes
				</button>
			</div>
		</div>
	</div>
{/if}
