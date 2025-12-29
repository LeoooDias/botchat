<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let value: string = '';

	const dispatch = createEventDispatcher<{ change: string }>();

	function handleFileUpload(event: Event) {
		const input = event.target as HTMLInputElement;
		const file = input.files?.[0];

		if (file) {
			const reader = new FileReader();
			reader.onload = (e) => {
				const content = e.target?.result as string;
				value = content;
				dispatch('change', content);
			};
			reader.readAsText(file);
		}
	}

	function handleTextChange() {
		dispatch('change', value);
	}

	function clearInstruction() {
		value = '';
		dispatch('change', '');
	}
</script>

<div class="space-y-3">
	<div>
		<label for="instruction-file" class="block text-sm font-medium text-gray-700 mb-2"> Upload File </label>
		<input
			id="instruction-file"
			type="file"
			accept=".txt,.md"
			on:change={handleFileUpload}
			class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
		/>
	</div>

	<div class="relative">
		<textarea
			bind:value
			on:change={handleTextChange}
			placeholder="Or paste bot instruction here..."
			rows="6"
			class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
		></textarea>
		{#if value}
			<button
				on:click={clearInstruction}
				class="absolute top-2 right-2 px-2 py-1 text-xs bg-gray-300 text-gray-700 rounded hover:bg-gray-400 transition"
			>
				Clear
			</button>
		{/if}
	</div>

	{#if value}
		<p class="text-xs text-gray-500">
			{value.length} characters
		</p>
	{/if}
</div>
