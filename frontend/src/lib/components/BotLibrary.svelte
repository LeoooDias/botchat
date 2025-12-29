<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { getMaxOutput } from '$lib/modelLimits';
	import AlertModal from './AlertModal.svelte';
	import { getUserItem, setUserItem, removeUserItem } from '$lib/utils/userStorage';

	interface Bot {
		id: string;
		provider: string;
		model: string;
		name?: string;
		systemInstructionText?: string;
		maxTokens?: number;
		category?: string;
	}

	interface Category {
		id: string;
		name: string;
	}

	export let savedBots: Bot[] = [];
	export let canAddToConversation: boolean = true; // Tier limit check
	export let currentBotsInConversation: number = 0; // Current count of bots in conversation
	export let maxBotsPerConversation: number = 10; // Max allowed bots per conversation

	const dispatch = createEventDispatcher<{ add: Bot; delete: string; update: Bot }>();

	const UNCATEGORIZED = 'Uncategorized';
	
	const providers = [
		{ name: 'Anthropic', value: 'anthropic', models: ['claude-sonnet-4-5', 'claude-haiku-4-5', 'claude-opus-4-5'] },
		{ name: 'Google', value: 'gemini', models: ['gemini-3-pro-preview', 'gemini-3-flash-preview', 'gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.5-pro'] },
		{ name: 'OpenAI', value: 'openai', models: ['gpt-5.2', 'gpt-5', 'gpt-5-nano','gpt-4.1', 'gpt-5-mini'] }
	];
	
	let isOpen = true;
	let editingBotId: string | null = null;
	let categories: Category[] = [];
	let collapsedCategories: Set<string> = new Set();
	let showInfoBox = true; // Persistent dismissal for info box
	
	// Category management state
	let showCategoryManager = false;
	let newCategoryName = '';
	let editingCategoryId: string | null = null;
	let editingCategoryName = '';
	
	// Clear All confirmation modal
	let showClearConfirmation = false;
	
	// Alert modal state
	let alertOpen = false;
	let alertTitle = '';
	let alertMessage = '';
	let alertType: 'info' | 'warning' | 'error' | 'success' = 'warning';
	
	function showAlert(title: string, message: string, type: 'info' | 'warning' | 'error' | 'success' = 'warning') {
		alertTitle = title;
		alertMessage = message;
		alertType = type;
		alertOpen = true;
	}
	
	// Copy feedback state
	let copiedBotId: string | null = null;
	
	// Max tokens validation for edit modal
	const MIN_TOKENS = 100;
	function getMaxTokensError(bot: Bot): string {
		if (!bot.maxTokens) return ''; // Empty is valid (will use default)
		if (bot.maxTokens < MIN_TOKENS) return `Minimum is ${MIN_TOKENS} tokens`;
		const modelMax = getMaxOutput(bot.provider, bot.model);
		if (modelMax && bot.maxTokens > modelMax) {
			return `Exceeds model limit of ${modelMax.toLocaleString()} tokens`;
		}
		return '';
	}

	// Provider color coding for bot cards
	const PROVIDER_COLORS: Record<string, { bg: string; border: string; hoverBorder: string }> = {
		'openai': {
			bg: 'bg-green-50 dark:bg-green-900/20',
			border: 'border-green-200 dark:border-green-800',
			hoverBorder: 'hover:border-green-400 dark:hover:border-green-600'
		},
		'anthropic': {
			bg: 'bg-orange-50 dark:bg-orange-900/20',
			border: 'border-orange-200 dark:border-orange-800',
			hoverBorder: 'hover:border-orange-400 dark:hover:border-orange-600'
		},
		'gemini': {
			bg: 'bg-blue-50 dark:bg-blue-900/20',
			border: 'border-blue-200 dark:border-blue-800',
			hoverBorder: 'hover:border-blue-400 dark:hover:border-blue-600'
		}
	};

	const DEFAULT_PROVIDER_COLOR = {
		bg: 'bg-gray-50 dark:bg-gray-700',
		border: 'border-gray-200 dark:border-gray-600',
		hoverBorder: 'hover:border-gray-400 dark:hover:border-gray-500'
	};

	function getProviderColor(provider: string) {
		return PROVIDER_COLORS[provider.toLowerCase()] || DEFAULT_PROVIDER_COLOR;
	}
	
	// Drag and drop state
	let draggedBotId: string | null = null;
	let dragOverCategory: string | null = null;

	onMount(() => {
		// Load categories from user-namespaced localStorage
		const storedCategories = getUserItem('botCategories');
		if (storedCategories) {
			try {
				const parsed = JSON.parse(storedCategories);
				// Filter out invalid categories (must have id and name)
				categories = parsed.filter((c: any) => c && c.id && c.name);
				// If we filtered out any invalid entries, save the cleaned version
				if (categories.length !== parsed.length) {
					saveCategories();
				}
			} catch (e) {
				console.error('Failed to load categories:', e);
				categories = [];
			}
		}
		
		// Load collapsed state
		const storedCollapsed = getUserItem('collapsedCategories');
		if (storedCollapsed) {
			try {
				collapsedCategories = new Set(JSON.parse(storedCollapsed));
			} catch (e) {
				collapsedCategories = new Set();
			}
		}
		
		// Load info box dismissed state
		showInfoBox = getUserItem('botLibraryInfoDismissed') !== 'true';

		// Listen for Escape key to close modals and Alt/Option+S to save
		const handleKeydown = (e: KeyboardEvent) => {
			if (e.key === 'Escape') {
				if (editingBotId) {
					cancelEdit();
				} else if (showClearConfirmation) {
					cancelClearAll();
				}
			} else if (e.altKey && e.code === 'KeyS' && editingBotId) {
				// Use e.code instead of e.key because Option+S produces 'ß' on Mac
				e.preventDefault();
				const bot = savedBots.find(b => b.id === editingBotId);
				if (bot) {
					saveEdit(bot);
				}
			}
		};
		document.addEventListener('keydown', handleKeydown);

		// Listen for categories updated event (e.g., from config import)
		const handleCategoriesUpdated = () => {
			const storedCategories = getUserItem('botCategories');
			if (storedCategories) {
				try {
					categories = JSON.parse(storedCategories);
				} catch (e) {
					console.error('Failed to reload categories:', e);
				}
			}
		};
		window.addEventListener('categoriesUpdated', handleCategoriesUpdated);

		return () => {
			document.removeEventListener('keydown', handleKeydown);
			window.removeEventListener('categoriesUpdated', handleCategoriesUpdated);
		};
	});

	function saveCategories() {
		setUserItem('botCategories', JSON.stringify(categories));
		// Dispatch a custom event so other components can update their category lists
		window.dispatchEvent(new CustomEvent('categoriesUpdated'));
	}

	function saveCollapsedState() {
		setUserItem('collapsedCategories', JSON.stringify([...collapsedCategories]));
	}

	function addBot(bot: Bot) {
		dispatch('add', bot);
	}

	function addCategoryBots(categoryName: string) {
		const bots = savedBots.filter((b) => (b.category || UNCATEGORIZED) === categoryName);
		
		// Check if adding all these bots would exceed the limit
		const totalAfterAdd = currentBotsInConversation + bots.length;
		if (totalAfterAdd > maxBotsPerConversation) {
			const available = maxBotsPerConversation - currentBotsInConversation;
			if (available <= 0) {
				showAlert('Bot Limit Reached', `Cannot add bots: chat already has ${currentBotsInConversation} bots (limit: ${maxBotsPerConversation}).`);
			} else {
				showAlert('Bot Limit Exceeded', `Cannot add ${bots.length} bots: would exceed limit of ${maxBotsPerConversation}. You can add ${available} more bot${available === 1 ? '' : 's'}.`);
			}
			return;
		}
		
		bots.forEach(addBot);
	}

	function deleteBot(botId: string) {
		savedBots = savedBots.filter((b) => b.id !== botId);
		// Persist
		const serializable = savedBots.map((b) => ({
			id: b.id,
			provider: b.provider,
			model: b.model,
			name: b.name,
			systemInstructionText: b.systemInstructionText,
			maxTokens: b.maxTokens,
			category: b.category
		}));
		setUserItem('savedBots', JSON.stringify(serializable));
		dispatch('delete', botId);
	}

	function startEdit(botId: string) {
		editingBotId = botId;
	}

	function saveEdit(updatedBot: Bot) {
		// Validate max tokens before saving
		if (getMaxTokensError(updatedBot)) return;
		
		const index = savedBots.findIndex((b) => b.id === updatedBot.id);
		if (index >= 0) {
			savedBots[index] = updatedBot;
			savedBots = savedBots;
			// Persist
			const serializable = savedBots.map((b) => ({
				id: b.id,
				provider: b.provider,
				model: b.model,
				name: b.name,
				systemInstructionText: b.systemInstructionText,
				maxTokens: b.maxTokens,
				category: b.category
			}));
			setUserItem('savedBots', JSON.stringify(serializable));
			dispatch('update', updatedBot);
		}
		editingBotId = null;
	}

	function cancelEdit() {
		editingBotId = null;
	}

	function showClearAllConfirmation() {
		showClearConfirmation = true;
	}

	function confirmClearAll() {
		savedBots = [];
		removeUserItem('savedBots');
		showClearConfirmation = false;
	}

	function cancelClearAll() {
		showClearConfirmation = false;
	}

	function toggleCategoryManager() {
		showCategoryManager = !showCategoryManager;
		if (showCategoryManager) {
			isOpen = true;
		}
	}

	// Category management functions
	function toggleCategory(categoryName: string) {
		if (collapsedCategories.has(categoryName)) {
			collapsedCategories.delete(categoryName);
		} else {
			collapsedCategories.add(categoryName);
		}
		collapsedCategories = collapsedCategories; // Trigger reactivity
		saveCollapsedState();
	}

	function createCategory() {
		if (!newCategoryName.trim()) return;
		if (newCategoryName.trim().toLowerCase() === UNCATEGORIZED.toLowerCase()) {
			showAlert('Invalid Name', 'Cannot create a category named "Uncategorized"');
			return;
		}
		if (categories.some(c => c.name.toLowerCase() === newCategoryName.trim().toLowerCase())) {
			showAlert('Duplicate Name', 'A category with this name already exists');
			return;
		}
		
		const newCategory: Category = {
			id: crypto.randomUUID(),
			name: newCategoryName.trim()
		};
		categories = [...categories, newCategory];
		saveCategories();
		newCategoryName = '';
	}

	function startEditCategory(category: Category) {
		editingCategoryId = category.id;
		editingCategoryName = category.name;
	}

	function saveEditCategory() {
		if (!editingCategoryName.trim() || !editingCategoryId) return;
		if (editingCategoryName.trim().toLowerCase() === UNCATEGORIZED.toLowerCase()) {
			showAlert('Invalid Name', 'Cannot rename to "Uncategorized"');
			return;
		}
		
		const oldCategory = categories.find(c => c.id === editingCategoryId);
		if (!oldCategory) return;
		
		const oldName = oldCategory.name;
		const newName = editingCategoryName.trim();
		
		// Check for duplicate names (excluding current category)
		if (categories.some(c => c.id !== editingCategoryId && c.name.toLowerCase() === newName.toLowerCase())) {
			showAlert('Duplicate Name', 'A category with this name already exists');
			return;
		}
		
		// Update category name
		categories = categories.map(c => 
			c.id === editingCategoryId ? { ...c, name: newName } : c
		);
		saveCategories();
		
		// Update bots in this category
		savedBots = savedBots.map(b => 
			b.category === oldName ? { ...b, category: newName } : b
		);
		persistBots();
		
		editingCategoryId = null;
		editingCategoryName = '';
	}

	function cancelEditCategory() {
		editingCategoryId = null;
		editingCategoryName = '';
	}

	function deleteCategory(categoryId: string) {
		const category = categories.find(c => c.id === categoryId);
		if (!category) return;
		
		const categoryName = category.name;
		
		// Move bots from deleted category to Uncategorized
		savedBots = savedBots.map(b => 
			b.category === categoryName ? { ...b, category: undefined } : b
		);
		persistBots();
		
		// Remove category
		categories = categories.filter(c => c.id !== categoryId);
		saveCategories();
		
		// Clean up collapsed state
		collapsedCategories.delete(categoryName);
		saveCollapsedState();
	}

	function persistBots() {
		const serializable = savedBots.map((b) => ({
			id: b.id,
			provider: b.provider,
			model: b.model,
			name: b.name,
			systemInstructionText: b.systemInstructionText,
			maxTokens: b.maxTokens,
			category: b.category
		}));
		setUserItem('savedBots', JSON.stringify(serializable));
	}

	// Svelte action to focus element on mount (accessibility-friendly alternative to autofocus)
	function focusOnMount(node: HTMLElement) {
		node.focus();
	}

	// Get bots grouped by category
	$: categorizedBots = (() => {
		const groups: Map<string, Bot[]> = new Map();
		
		// Initialize groups for all categories
		groups.set(UNCATEGORIZED, []);
		categories.forEach(c => groups.set(c.name, []));
		
		// Group bots
		savedBots.forEach(bot => {
			const categoryName = bot.category || UNCATEGORIZED;
			if (!groups.has(categoryName)) {
				// Category was deleted, move to uncategorized
				groups.get(UNCATEGORIZED)!.push(bot);
			} else {
				groups.get(categoryName)!.push(bot);
			}
		});
		
		// Sort bots alphabetically by name within each category
		groups.forEach((bots, _category) => {
			bots.sort((a, b) => {
				const nameA = (a.name || a.model).toLowerCase();
				const nameB = (b.name || b.model).toLowerCase();
				return nameA.localeCompare(nameB);
			});
		});
		
		return groups;
	})();

	// Get ordered category names (Uncategorized first, then custom categories alphabetically)
	$: orderedCategories = [UNCATEGORIZED, ...categories.map(c => c.name).filter(name => name !== UNCATEGORIZED).sort()];
</script>

<div class="border-b dark:border-gray-700 pb-4">
	<div class="flex items-center justify-between">
		<button
			on:click={() => (isOpen = !isOpen)}
			class="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition touch-target py-2"
		>
			<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5M4.5 12H3m18 0h-1.5m-15 3.75H3m18 0h-1.5M8.25 19.5V21M12 3v1.5m0 15V21m3.75-18v1.5m0 15V21m-9-1.5h10.5a2.25 2.25 0 002.25-2.25V6.75a2.25 2.25 0 00-2.25-2.25H6.75A2.25 2.25 0 004.5 6.75v10.5a2.25 2.25 0 002.25 2.25zm.75-12h9v9h-9v-9z" />
			</svg>
			<span>Bots ({savedBots.length})</span>
			<span class="text-lg ml-2">{isOpen ? '▼' : '▶'}</span>
		</button>
		<div class="flex items-center gap-3">
			<button
				type="button"
				on:click|preventDefault|stopPropagation={toggleCategoryManager}
				class="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition cursor-pointer py-2 px-1"
				title="Manage categories"
			>
				Categories
			</button>
			{#if savedBots.length > 0}
				<button
					type="button"
					on:click={showClearAllConfirmation}
					class="text-xs text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 transition py-2 px-1"
					title="Delete all saved bots from browser storage"
				>
					Clear All
				</button>
			{/if}
		</div>
	</div>

	{#if isOpen}
		<!-- Category Manager -->
		{#if showCategoryManager}
			<div class="mt-3 bg-gray-50 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700 rounded p-3 mb-3">
				<h4 class="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Manage Categories</h4>
				
				<!-- Create new category -->
				<div class="flex gap-2 mb-3">
					<input
						type="text"
						bind:value={newCategoryName}
						placeholder="New category name..."
						on:keydown={(e) => e.key === 'Enter' && createCategory()}
						class="flex-1 px-2 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:ring-1 focus:ring-inset focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
					/>
					<button
						on:click={createCategory}
						disabled={!newCategoryName.trim()}
						class="px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition"
					>
						Add
					</button>
				</div>
				
				<!-- List existing categories -->
				{#if categories.length > 0}
					<div class="space-y-1">
						{#each categories as category (category.id)}
							<div class="flex items-center justify-between bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded px-2 py-1">
								{#if editingCategoryId === category.id}
									<input
										type="text"
										bind:value={editingCategoryName}
										on:keydown={(e) => {
											if (e.key === 'Enter') saveEditCategory();
											if (e.key === 'Escape') cancelEditCategory();
										}}
										class="flex-1 px-1 py-0.5 text-xs border border-blue-400 rounded focus:outline-none dark:bg-gray-700 dark:text-white"
										use:focusOnMount
									/>
									<div class="flex gap-1 ml-2">
										<button
											on:click={saveEditCategory}
											class="text-xs text-green-600 dark:text-green-400 hover:text-green-800"
											title="Save"
										>✓</button>
										<button
											on:click={cancelEditCategory}
											class="text-xs text-gray-500 hover:text-gray-700"
											title="Cancel"
										>✕</button>
									</div>
								{:else}
									<span class="text-xs text-gray-700 dark:text-gray-300">{category.name}</span>
									<div class="flex gap-1">
										<button
											on:click={() => startEditCategory(category)}
											class="text-xs text-amber-600 dark:text-amber-400 hover:text-amber-800"
											title="Rename category"
										>✎</button>
										<button
											on:click={() => deleteCategory(category.id)}
											class="text-xs text-red-600 dark:text-red-400 hover:text-red-800"
											title="Delete category"
										>✕</button>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-xs text-gray-500 dark:text-gray-400 italic">No custom categories yet.</p>
				{/if}
			</div>
		{/if}

		{#if showInfoBox}
			<div class="mt-3 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded p-2 mb-3 flex items-start justify-between gap-2">
				<p class="text-sm md:text-xs text-blue-800 dark:text-blue-200">
					Bots are saved in your browser's local storage. They persist until you delete them.
				</p>
				<button
				on:click|stopPropagation={() => { showInfoBox = false; setUserItem('botLibraryInfoDismissed', 'true'); }}
				class="flex-shrink-0 w-8 h-8 md:w-auto md:h-auto flex items-center justify-center text-sm md:text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-800/50 rounded transition"
				title="Dismiss this message permanently"
				>
					✕
				</button>
			</div>
		{/if}
		
		<div class="space-y-2">
			{#if savedBots.length === 0}
				<p class="text-xs text-gray-500 dark:text-gray-400 italic">No bots yet. Create one below!</p>
			{:else}
				{#each orderedCategories as categoryName}
					{@const botsInCategory = categorizedBots.get(categoryName) || []}
					{@const wouldExceedLimit = currentBotsInConversation + botsInCategory.length > maxBotsPerConversation}
					{#if botsInCategory.length > 0 || categoryName !== UNCATEGORIZED}
							<div class="border border-gray-200 dark:border-gray-600 rounded overflow-hidden">
								<!-- Category Header -->
								<div class="w-full flex items-center justify-between bg-gray-100 dark:bg-gray-700">
									<button
										on:click={() => toggleCategory(categoryName)}
										class="flex items-center gap-2 flex-1 px-3 py-2.5 md:px-2 md:py-1.5 text-sm md:text-xs font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white hover:bg-gray-200 dark:hover:bg-gray-600 transition text-left"
										title="Expand or collapse category"
									>
										<span class="text-gray-500 dark:text-gray-400">{collapsedCategories.has(categoryName) ? '▶' : '▼'}</span>
									{#if categoryName === UNCATEGORIZED}
										<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776" />
										</svg>
									{:else}
										<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z" />
										</svg>
									{/if}
									<span>{categoryName}</span>
										<span class="text-gray-500 dark:text-gray-400">({botsInCategory.length})</span>
									</button>
									<button
										on:click={(e) => {
											e.stopPropagation();
											addCategoryBots(categoryName);
										}}
										class="px-3 py-2 md:px-2 md:py-1 text-sm md:text-xs rounded transition mx-2 min-w-[44px] min-h-[44px] md:min-w-0 md:min-h-0 flex items-center justify-center {wouldExceedLimit ? 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed' : 'bg-blue-600 text-white hover:bg-blue-700'}"
										title={wouldExceedLimit ? `Adding ${botsInCategory.length} bots would exceed limit of ${maxBotsPerConversation}` : 'Add all bots in this category'}
										disabled={wouldExceedLimit}
									>
										+
									</button>
								</div>
							
						<!-- Category Content -->
						{#if !collapsedCategories.has(categoryName)}
							<div 
								role="region"
								aria-label="Drag and drop zone for {categoryName}"
								on:dragover={(e) => {
									e.preventDefault();
									if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
									dragOverCategory = categoryName;
								}}
								on:dragleave={() => {
									dragOverCategory = null;
								}}
								on:drop={(e) => {
									e.preventDefault();
									if (draggedBotId && draggedBotId !== '') {
										const bot = savedBots.find(b => b.id === draggedBotId);
										if (bot && bot.category !== categoryName) {
											bot.category = categoryName === UNCATEGORIZED ? undefined : categoryName;
											saveEdit(bot);
										}
									}
									dragOverCategory = null;
								}}
								class="p-2 space-y-2 bg-white dark:bg-gray-800 {dragOverCategory === categoryName ? 'ring-2 ring-blue-400 dark:ring-blue-500 bg-blue-50 dark:bg-blue-900/20' : ''}"
							>
								{#if botsInCategory.length === 0}
										<p class="text-xs text-gray-400 dark:text-gray-500 italic px-1">No bots in this category</p>
									{:else}
										{#each botsInCategory as bot (bot.id)}
												{@const colors = getProviderColor(bot.provider)}
												<div 
													role="button"
													tabindex="0"
													draggable="true"
													on:dragstart={(e) => {
														draggedBotId = bot.id;
														if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
													}}
													on:dragend={() => {
														draggedBotId = null;
														dragOverCategory = null;
													}}
													class="flex items-center justify-between {colors.bg} border {colors.border} rounded p-3 md:p-2 {colors.hoverBorder} transition cursor-move {draggedBotId === bot.id ? 'opacity-50' : ''}"
												>
												<div class="flex-1 min-w-0">
													<p class="text-sm md:text-xs font-semibold text-gray-900 dark:text-white">{bot.name || bot.provider}</p>
													<p class="text-sm md:text-xs text-gray-600 dark:text-gray-300 truncate">{bot.model}</p>
													{#if bot.maxTokens}
														<p class="text-sm md:text-xs text-blue-600 dark:text-blue-400">max_tokens: {bot.maxTokens}</p>
													{/if}
												</div>
												<div class="flex gap-2 md:gap-1 ml-2 flex-shrink-0">
													<button
														on:click={() => addBot(bot)}
														class="w-11 h-11 md:w-auto md:h-auto md:px-2 md:py-1 text-sm md:text-xs rounded transition flex items-center justify-center {canAddToConversation ? 'bg-blue-600 text-white hover:bg-blue-700' : 'bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 cursor-not-allowed'}"
														title={canAddToConversation ? 'Add to chat' : 'Chat bot limit reached'}
														disabled={!canAddToConversation}
													>
														+
													</button>
													<button
														on:click={() => startEdit(bot.id)}
														class="w-11 h-11 md:w-auto md:h-auto md:px-2 md:py-1 text-sm md:text-xs bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 rounded hover:bg-amber-200 dark:hover:bg-amber-900 transition flex items-center justify-center"
														title="Edit bot"
													>
														✎
													</button>
													<button
														on:click={() => deleteBot(bot.id)}
														class="w-11 h-11 md:w-auto md:h-auto md:px-2 md:py-1 text-sm md:text-xs bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900 transition flex items-center justify-center"
														title="Delete from library"
													>
														✕
													</button>
												</div>
											</div>

											<!-- Edit Dialog for this bot -->
											{#if editingBotId === bot.id}
												<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
													<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 w-full max-w-md mx-4">
														<h2 class="text-lg font-bold text-gray-900 dark:text-white mb-4">Edit Bot</h2>

														<div class="space-y-4">
															<!-- Bot Name -->
															<div>
																<label for="edit-name-{bot.id}" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
																	Name
																</label>
																<input
																	id="edit-name-{bot.id}"
																	type="text"
																	value={bot.name}
																	on:change={(e) => (bot.name = e.currentTarget.value)}
																	on:keydown={(e) => e.key === 'Enter' && saveEdit(bot)}
																	placeholder="e.g., Code Reviewer"
																	class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
																/>
															</div>

															<!-- Category -->
															<div>
																<label for="edit-category-{bot.id}" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
																	Category
																</label>
																<select
																	id="edit-category-{bot.id}"
																	value={bot.category || ''}
																	on:change={(e) => (bot.category = e.currentTarget.value || undefined)}
																	class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
																>
																	<option value="">Uncategorized</option>
																	{#each categories.filter(c => c.name !== UNCATEGORIZED) as cat}
																		<option value={cat.name}>{cat.name}</option>
																	{/each}
																</select>
															</div>

															<!-- Provider & Model -->
															<div class="grid grid-cols-2 gap-3">
																<div>
																	<label for="edit-provider-{bot.id}" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Provider</label>
																	<select
																		id="edit-provider-{bot.id}"
																		value={bot.provider}
																		on:change={(e) => {
																			bot.provider = e.currentTarget.value;
																			// Reset model when provider changes
																			const providerData = providers.find(p => p.value === bot.provider);
																			if (providerData && !providerData.models.includes(bot.model)) {
																				bot.model = providerData.models[0];
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
																	<label for="edit-model-{bot.id}" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Model</label>
																	<select
																		id="edit-model-{bot.id}"
																		value={bot.model}
																		on:change={(e) => (bot.model = e.currentTarget.value)}
																		class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
																	>
																		{#each (providers.find(p => p.value === bot.provider)?.models || []) as model}
																			<option value={model}>{model}</option>
																		{/each}
																	</select>
																</div>
															</div>

															<!-- Bot Instruction -->
															<div>
																<div class="flex justify-between items-center mb-1">
																	<label for="edit-system-{bot.id}" class="text-sm font-medium text-gray-700 dark:text-gray-300">
																		Bot Instruction (optional)
																	</label>
																	<button
																		type="button"
																		on:click={() => {
																			if (bot.systemInstructionText) {
																				navigator.clipboard.writeText(bot.systemInstructionText);
																				copiedBotId = bot.id;
																				setTimeout(() => {
																					copiedBotId = null;
																				}, 2000);
																			}
																		}}
																		class="p-1 {copiedBotId === bot.id ? 'text-green-500' : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'} transition"
																		title={copiedBotId === bot.id ? 'Copied!' : 'Copy to clipboard'}
																	>
																		{#if copiedBotId === bot.id}
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
																	id="edit-system-{bot.id}"
																	value={bot.systemInstructionText || ''}
																	on:change={(e) => (bot.systemInstructionText = e.currentTarget.value)}
																	placeholder="Enter bot instruction..."
																	rows="4"
																	class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500 font-mono text-xs dark:bg-gray-700 dark:text-white dark:placeholder-gray-400"
																></textarea>
															</div>

															<!-- Max Tokens -->
															<div>
																<label for="edit-max-tokens-{bot.id}" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
																	Max Tokens (optional)
																</label>
																<input
																	id="edit-max-tokens-{bot.id}"
																	type="number"
																	value={bot.maxTokens || ''}
																	on:change={(e) => (bot.maxTokens = e.currentTarget.value ? parseInt(e.currentTarget.value) : undefined)}
																	on:keydown={(e) => e.key === 'Enter' && !getMaxTokensError(bot) && saveEdit(bot)}
																	placeholder={getMaxOutput(bot.provider, bot.model) ? `${MIN_TOKENS} – ${getMaxOutput(bot.provider, bot.model)?.toLocaleString()}` : 'Leave empty for default'}
																	min={MIN_TOKENS}
																	max={getMaxOutput(bot.provider, bot.model) || undefined}
																	class="w-full px-3 py-2 border rounded text-sm focus:outline-none focus:ring-2 focus:ring-inset dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 {getMaxTokensError(bot) ? 'border-red-500 focus:ring-red-500' : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500'}"
																/>
																{#if getMaxTokensError(bot)}
																	<p class="text-xs text-red-600 dark:text-red-400 mt-1 flex items-center gap-1">
																		<svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
																			<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
																		</svg>
																		{getMaxTokensError(bot)}
																	</p>
																{:else}
																	<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
																		Range: {MIN_TOKENS} – {getMaxOutput(bot.provider, bot.model)?.toLocaleString() || 'unlimited'}
																	</p>
																{/if}
															</div>
														</div>

														<!-- Buttons -->
														<div class="flex gap-2 mt-6">
															<button
																on:click={cancelEdit}
																class="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition font-medium text-sm"
															>
																Cancel
															</button>
															<button
																on:click={() => saveEdit(bot)}
																disabled={!!getMaxTokensError(bot)}
																class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition font-medium text-sm"
															>
																Save Changes
															</button>
														</div>
													</div>
												</div>
											{/if}
										{/each}
									{/if}
							</div>
							{/if}
						</div>
					{/if}
				{/each}
			{/if}
		</div>
	{/if}
</div>

<!-- Clear All Confirmation Modal -->
{#if showClearConfirmation}
	<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 w-full max-w-sm mx-4">
			<div class="text-center">
				<div class="flex justify-center mb-4">
					<svg class="w-12 h-12 text-amber-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
					</svg>
				</div>
				<h2 class="text-lg font-bold text-gray-900 dark:text-white mb-2">Clear All Bots?</h2>
				<p class="text-sm text-gray-600 dark:text-gray-400 mb-6">
					{#if savedBots.length === 1}
						This will permanently delete the 1 saved bot from your library. Categories will be preserved, but the bot will be removed. This action cannot be undone.
					{:else}
						This will permanently delete all {savedBots.length} saved bots from your library. Categories will be preserved, but all bots will be removed. This action cannot be undone.
					{/if}
				</p>
				<div class="flex gap-3">
					<button
						on:click={cancelClearAll}
						class="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition font-medium text-sm"
					>
						Cancel
					</button>
					<button
						on:click={confirmClearAll}
						class="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition font-medium text-sm"
					>
						Clear All
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Alert Modal -->
<AlertModal
	bind:isOpen={alertOpen}
	title={alertTitle}
	message={alertMessage}
	type={alertType}
	on:confirm={() => alertOpen = false}
	on:close={() => alertOpen = false}
/>
