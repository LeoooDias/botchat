<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { fade, scale, fly } from 'svelte/transition';
	import { quintOut, backOut } from 'svelte/easing';

	export let isOpen = false;

	const dispatch = createEventDispatcher<{ 
		close: void; 
		generate: { name: string; instruction: string } 
	}>();

	// API base URL
	const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

	// State
	let words: string[] = [];
	let selectedWords: string[] = [];
	let customWords: string[] = [];
	let customWordInput = '';
	let botName = '';
	let roundNumber = 1;
	let isLoadingWords = false;
	let isGenerating = false;
	let generatedInstruction = '';
	let showPreview = false;
	let error = '';

	// Animation state for word grid
	let wordAnimationKey = 0;

	// Minimum words needed before generating
	const MIN_WORDS = 5;

	$: totalSelected = selectedWords.length + customWords.length;
	$: canGenerate = totalSelected >= MIN_WORDS && botName.trim().length > 0;
	$: canRefresh = !isLoadingWords;

	// Reset state when modal opens
	$: if (isOpen) {
		resetWizard();
		loadInitialWords();
	}

	function resetWizard() {
		words = [];
		selectedWords = [];
		customWords = [];
		customWordInput = '';
		botName = '';
		roundNumber = 1;
		generatedInstruction = '';
		showPreview = false;
		error = '';
	}

	async function loadInitialWords() {
		await fetchWords();
	}

	async function fetchWords() {
		isLoadingWords = true;
		error = '';
		
		try {
			const response = await fetch(`${API_BASE}/wizard/words`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					selected_words: selectedWords,
					round_number: roundNumber
				})
			});

			if (!response.ok) {
				throw new Error('Failed to load words');
			}

			const data = await response.json();
			words = data.words;
			wordAnimationKey++; // Trigger re-animation
			roundNumber++;
		} catch (e) {
			console.error('Failed to fetch words:', e);
			// Silently fall back to default words - no need to alarm the user
			words = [
				'analytical', 'empathetic', 'strategic', 'concise',
				'creative', 'cautious', 'bold', 'methodical',
				'pragmatic', 'visionary', 'detail-oriented', 'big-picture',
				'collaborative', 'independent', 'patient', 'decisive'
			];
			wordAnimationKey++;
		} finally {
			isLoadingWords = false;
		}
	}

	function toggleWord(word: string) {
		if (selectedWords.includes(word)) {
			selectedWords = selectedWords.filter(w => w !== word);
		} else {
			selectedWords = [...selectedWords, word];
		}
	}

	function addCustomWord() {
		const word = customWordInput.trim().toLowerCase();
		if (word && !customWords.includes(word) && !selectedWords.includes(word)) {
			customWords = [...customWords, word];
			customWordInput = '';
		}
	}

	function removeCustomWord(word: string) {
		customWords = customWords.filter(w => w !== word);
	}

	function removeSelectedWord(word: string) {
		selectedWords = selectedWords.filter(w => w !== word);
	}

	async function generatePersona() {
		if (!canGenerate) return;
		
		isGenerating = true;
		error = '';

		try {
			const response = await fetch(`${API_BASE}/wizard/generate`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					name: botName.trim(),
					selected_words: selectedWords,
					custom_words: customWords
				})
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || 'Failed to generate persona');
			}

			const data = await response.json();
			generatedInstruction = data.instruction;
			showPreview = true;
		} catch (e) {
			console.error('Failed to generate persona:', e);
			error = e instanceof Error ? e.message : 'Failed to generate persona. Please try again.';
		} finally {
			isGenerating = false;
		}
	}

	function acceptPersona() {
		dispatch('generate', {
			name: botName.trim(),
			instruction: generatedInstruction
		});
		handleClose();
	}

	function regeneratePersona() {
		showPreview = false;
		generatePersona();
	}

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
			if (showPreview) {
				showPreview = false;
			} else {
				handleClose();
			}
		}
	}

	function handleCustomWordKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addCustomWord();
		}
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
	<!-- Modal Backdrop -->
	<div
		class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4"
		on:click={handleBackdropClick}
		on:keydown={() => {}}
		role="dialog"
		aria-modal="true"
		aria-labelledby="wizard-title"
		tabindex="-1"
		transition:fade={{ duration: 200 }}
	>
		<!-- Modal Content -->
		<div 
			class="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden border border-gray-200 dark:border-gray-700"
			transition:scale={{ duration: 300, easing: backOut, start: 0.95 }}
		>
			<!-- Header -->
			<div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center gap-3">
					<div class="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
						<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
						</svg>
					</div>
					<div>
						<h2 id="wizard-title" class="text-xl font-bold text-gray-900 dark:text-white">Persona Wizard</h2>
						<p class="text-sm text-gray-500 dark:text-gray-400">Craft your AI advisor's personality</p>
					</div>
				</div>
				<button
					on:click={handleClose}
					class="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition"
					aria-label="Close"
				>
					<svg class="w-5 h-5 text-gray-500 dark:text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Content -->
			<div class="flex-1 overflow-y-auto p-6">
				{#if showPreview}
					<!-- Preview Screen -->
					<div transition:fly={{ y: 20, duration: 300 }}>
						<div class="mb-4">
							<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-1">
								Meet {botName}
							</h3>
							<p class="text-sm text-gray-500 dark:text-gray-400">
								Review your persona and make adjustments if needed.
							</p>
						</div>
						
						<div class="bg-gray-50 dark:bg-gray-800 rounded-xl p-4 mb-4 max-h-[40vh] overflow-y-auto">
							<pre class="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300 font-mono leading-relaxed">{generatedInstruction}</pre>
						</div>

						<div class="flex gap-3">
							<button
								on:click={regeneratePersona}
								disabled={isGenerating}
								class="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition font-medium disabled:opacity-50"
							>
								{#if isGenerating}
									<span class="flex items-center justify-center gap-2">
										<svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
											<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
											<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
										</svg>
										Regenerating...
									</span>
								{:else}
									↻ Regenerate
								{/if}
							</button>
							<button
								on:click={acceptPersona}
								class="flex-1 px-4 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl hover:from-blue-600 hover:to-blue-700 transition font-medium shadow-lg shadow-blue-500/25"
							>
								Use This Persona ✓
							</button>
						</div>
					</div>
				{:else}
					<!-- Selection Screen -->
					<!-- Name Input -->
					<div class="mb-6">
						<label for="persona-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
							Name your advisor
						</label>
						<input
							id="persona-name"
							type="text"
							bind:value={botName}
							placeholder="e.g., Catherine, Marcus, The Strategist..."
							class="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
						/>
					</div>

					<!-- Selected Words Pills -->
					{#if selectedWords.length > 0 || customWords.length > 0}
						<div class="mb-4" transition:fly={{ y: -10, duration: 200 }}>
							<p class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
								Selected traits ({totalSelected})
							</p>
							<div class="flex flex-wrap gap-2">
								{#each selectedWords as word (word)}
									<button
										on:click={() => removeSelectedWord(word)}
										class="px-3 py-1.5 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium flex items-center gap-1.5 hover:bg-blue-200 dark:hover:bg-blue-900 transition group"
										transition:scale={{ duration: 150 }}
									>
										{word}
										<svg class="w-3.5 h-3.5 opacity-50 group-hover:opacity-100" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
										</svg>
									</button>
								{/each}
								{#each customWords as word (word)}
									<button
										on:click={() => removeCustomWord(word)}
										class="px-3 py-1.5 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium flex items-center gap-1.5 hover:bg-blue-200 dark:hover:bg-blue-900 transition group"
										transition:scale={{ duration: 150 }}
									>
										{word}
										<svg class="w-3.5 h-3.5 opacity-50 group-hover:opacity-100" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
										</svg>
									</button>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Word Grid -->
					<div class="mb-4">
						<div class="flex items-center justify-between mb-3">
							<p class="text-sm text-gray-600 dark:text-gray-400">
								Select traits that resonate
							</p>
							<button
								on:click={fetchWords}
								disabled={!canRefresh}
								class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition disabled:opacity-50"
								title="Load new words"
							>
								<svg 
									class="w-4 h-4 {isLoadingWords ? 'animate-spin' : ''}" 
									fill="none" 
									stroke="currentColor" 
									viewBox="0 0 24 24"
								>
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
								</svg>
								Refresh
							</button>
						</div>

						{#if error}
							<div class="mb-4 p-3 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg text-sm">
								{error}
							</div>
						{/if}

						{#key wordAnimationKey}
							<div class="grid grid-cols-4 gap-2">
								{#each words as word, i (word + '-' + i)}
									<button
										on:click={() => toggleWord(word)}
										disabled={selectedWords.includes(word)}
										class="px-3 py-2.5 text-sm font-medium rounded-xl transition-all duration-200 {selectedWords.includes(word) 
													? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30 scale-95' 
											: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 hover:scale-[1.02]'}"
										style="animation-delay: {i * 30}ms"
										in:fly={{ y: 10, duration: 200, delay: i * 30 }}
									>
										{word}
									</button>
								{/each}
							</div>
						{/key}
					</div>

					<!-- Custom Word Input -->
					<div class="mb-6">
						<label for="custom-word" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
							Add your own
						</label>
						<div class="flex gap-2">
							<input
								id="custom-word"
								type="text"
								bind:value={customWordInput}
								on:keydown={handleCustomWordKeydown}
								placeholder="Type a trait and press Enter..."
								class="flex-1 px-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
							/>
							<button
								on:click={addCustomWord}
								disabled={!customWordInput.trim()}
								class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-300 dark:hover:bg-gray-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
							>
								Add
							</button>
						</div>
					</div>
				{/if}
			</div>

			<!-- Footer -->
			{#if !showPreview}
				<div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
					<div class="flex items-center justify-between">
						<p class="text-sm text-gray-500 dark:text-gray-400">
							{#if totalSelected < MIN_WORDS}
								Select at least {MIN_WORDS - totalSelected} more trait{MIN_WORDS - totalSelected !== 1 ? 's' : ''}
							{:else if !botName.trim()}
								Enter a name to continue
							{:else}
								Ready to generate!
							{/if}
						</p>
						<button
							on:click={generatePersona}
							disabled={!canGenerate || isGenerating}
							class="px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:from-gray-400 disabled:to-gray-500 enabled:hover:from-blue-600 enabled:hover:to-blue-700 enabled:shadow-lg enabled:shadow-blue-500/25 flex items-center gap-2"
						>
							{#if isGenerating}
								<svg class="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
								Generating...
							{:else}
								<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
								</svg>
								Generate Persona
							{/if}
						</button>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}
