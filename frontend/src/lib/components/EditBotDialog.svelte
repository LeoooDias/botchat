<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	interface Bot {
		id: string;
		provider: string;
		model: string;
		name?: string;
		systemInstructionText?: string;
		maxTokens?: number;
	}

	export let bot: Bot | null = null;
	export let isOpen = false;

	const dispatch = createEventDispatcher<{ save: Bot; cancel: void }>();

	let editedBot: Bot | null = null;

	$: if (bot && isOpen) {
		editedBot = { ...bot };
	}

	function handleSave() {
		if (editedBot) {
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
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen && editedBot}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
		<div class="bg-white rounded-lg shadow-lg p-6 w-full max-w-md mx-4">
			<h2 class="text-lg font-bold text-gray-900 mb-4">Edit Bot</h2>

			<div class="space-y-4">
				<!-- Bot Name -->
				<div>
					<label for="edit-name" class="block text-sm font-medium text-gray-700 mb-1">
						Name
					</label>
					<input
						id="edit-name"
						type="text"
						bind:value={editedBot.name}
						placeholder="e.g., Code Reviewer"
						class="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
						on:keydown={(e) => e.key === 'Enter' && handleSave()}
					/>
				</div>

				<!-- Provider & Model -->
				<div class="grid grid-cols-2 gap-3">
					<div>
						<label for="edit-provider" class="block text-sm font-medium text-gray-700 mb-1">Provider</label>
						<input
							id="edit-provider"
							type="text"
							bind:value={editedBot.provider}
							class="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
						/>
					</div>
					<div>
						<label for="edit-model" class="block text-sm font-medium text-gray-700 mb-1">Model</label>
						<input
							id="edit-model"
							type="text"
							bind:value={editedBot.model}
							class="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
						/>
					</div>
				</div>

				<!-- Bot Instruction -->
				<div>
					<label for="edit-system" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						Bot Instruction (optional)
					</label>
					<textarea
						id="edit-system"
						bind:value={editedBot.systemInstructionText}
						placeholder="Enter bot instruction..."
						rows="4"
						class="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-xs"
					></textarea>
				</div>

				<!-- Max Tokens -->
				<div>
					<label for="edit-max-tokens" class="block text-sm font-medium text-gray-700 mb-1">
						Max Tokens (optional)
					</label>
					<input
						id="edit-max-tokens"
						type="number"
						bind:value={editedBot.maxTokens}
						placeholder="Leave empty for default"
						min="1"
						class="w-full px-3 py-2 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
					/>
					<p class="text-xs text-gray-500 mt-1">
						Higher values allow longer responses but may hit token limits with large documents.
					</p>
				</div>
			</div>

			<!-- Buttons -->
			<div class="flex gap-2 mt-6">
				<button
					on:click={handleCancel}
					class="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition font-medium text-sm"
				>
					Cancel
				</button>
				<button
					on:click={handleSave}
					class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium text-sm"
				>
					Save Changes
				</button>
			</div>
		</div>
	</div>
{/if}
