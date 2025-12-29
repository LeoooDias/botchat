<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	interface SelectedModel {
		id: string;
		provider: string;
		model: string;
	}

	export let selectedModels: SelectedModel[] = [];

	const dispatch = createEventDispatcher<{ select: SelectedModel[] }>();

	const providers = [
		{ name: 'Anthropic', value: 'anthropic', models: ['claude-sonnet-4-5', 'claude-haiku-4-5', 'claude-opus-4-5'] },
		{ name: 'Google', value: 'gemini', models: ['gemini-3-pro-preview', 'gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'] },
		{ name: 'OpenAI', value: 'openai', models: ['gpt-5.2', 'gpt-5', 'gpt-5-nano','gpt-4.1', 'gpt-5-mini'] }
	];

	let selectedProvider: string = '';
	let selectedModel: string = '';

	function addModel() {
		if (!selectedProvider || !selectedModel) return;

		const newModel: SelectedModel = {
			id: crypto.randomUUID(),
			provider: selectedProvider,
			model: selectedModel
		};

		selectedModels = [...selectedModels, newModel];
		dispatch('select', selectedModels);

		selectedProvider = '';
		selectedModel = '';
	}

	function removeModel(id: string) {
		selectedModels = selectedModels.filter((m) => m.id !== id);
		dispatch('select', selectedModels);
	}

	$: availableModels = providers.find((p) => p.value === selectedProvider)?.models || [];
</script>

<div class="space-y-3">
	<div class="flex gap-2">
		<select bind:value={selectedProvider} class="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm">
			<option value="">Provider</option>
			{#each providers as p}
				<option value={p.value}>{p.name}</option>
			{/each}
		</select>

		<select
			bind:value={selectedModel}
			disabled={!selectedProvider}
			class="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm disabled:bg-gray-100"
		>
			<option value="">Model</option>
			{#each availableModels as m}
				<option value={m}>{m}</option>
			{/each}
		</select>

		<button
			on:click={addModel}
			disabled={!selectedProvider || !selectedModel}
			class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition font-medium"
		>
			Add
		</button>
	</div>

	<div class="space-y-2">
		{#each selectedModels as model (model.id)}
			<div class="flex flex-col gap-2 bg-white border border-gray-300 rounded-lg p-3">
				<div class="flex-1 min-w-0">
					<p class="font-semibold text-sm text-gray-900">{model.provider}</p>
					<p class="text-xs text-gray-600 break-words">{model.model}</p>
				</div>
				<button
					on:click={() => removeModel(model.id)}
					class="w-full px-3 py-1 text-sm bg-red-100 text-red-700 rounded hover:bg-red-200 transition"
				>
					Remove
				</button>
			</div>
		{/each}

		{#if selectedModels.length === 0}
			<p class="text-sm text-gray-500 py-3 text-center">No models selected</p>
		{/if}
	</div>
</div>
