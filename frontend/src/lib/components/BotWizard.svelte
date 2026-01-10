<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { fade, scale, fly, slide } from 'svelte/transition';
	import { quintOut, backOut } from 'svelte/easing';

	export let isOpen = false;

	const dispatch = createEventDispatcher<{ 
		close: void; 
		generate: { name: string; instruction: string } 
	}>();

	// API base URL
	const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

	// Expertise taxonomy (loaded from config)
	interface Subclass {
		id: string;
		name: string;
		keywords: string[];
	}
	interface Category {
		id: string;
		name: string;
		description: string;
		subclasses: Subclass[];
	}

	const taxonomy: Category[] = [
		{
			id: "natural-sciences",
			name: "Natural Sciences",
			description: "The systematic study of the natural world",
			subclasses: [
				{ id: "evolutionary-biology", name: "Evolutionary Biology", keywords: ["evolution", "natural selection", "speciation"] },
				{ id: "molecular-biology", name: "Molecular & Cellular Biology", keywords: ["genetics", "DNA", "proteins", "cell biology"] },
				{ id: "ecology", name: "Ecology & Environmental Science", keywords: ["ecosystems", "conservation", "biodiversity"] },
				{ id: "physics", name: "Physics", keywords: ["quantum mechanics", "relativity", "thermodynamics"] },
				{ id: "chemistry", name: "Chemistry & Materials Science", keywords: ["organic chemistry", "polymers", "nanotechnology"] },
				{ id: "astronomy", name: "Astronomy & Cosmology", keywords: ["astrophysics", "planetary science", "cosmology"] },
				{ id: "mathematics", name: "Mathematics", keywords: ["pure math", "applied math", "statistics", "probability"] },
				{ id: "earth-sciences", name: "Earth Sciences", keywords: ["geology", "oceanography", "meteorology"] },
				{ id: "neuroscience", name: "Neuroscience & Cognitive Science", keywords: ["brain", "cognition", "consciousness"] }
			]
		},
		{
			id: "technology",
			name: "Technology",
			description: "The application of scientific knowledge for practical purposes",
			subclasses: [
				{ id: "software-engineering", name: "Software Engineering", keywords: ["programming", "architecture", "DevOps"] },
				{ id: "computer-science", name: "Computer Science & Algorithms", keywords: ["data structures", "distributed systems", "databases"] },
				{ id: "artificial-intelligence", name: "Artificial Intelligence & ML", keywords: ["machine learning", "deep learning", "NLP"] },
				{ id: "cybersecurity", name: "Cybersecurity", keywords: ["cryptography", "network security", "incident response"] },
				{ id: "medicine", name: "Medicine & Healthcare", keywords: ["clinical medicine", "surgery", "pharmacology"] },
				{ id: "civil-engineering", name: "Civil & Structural Engineering", keywords: ["construction", "infrastructure", "materials"] },
				{ id: "electrical-engineering", name: "Electrical & Electronics", keywords: ["circuits", "power systems", "semiconductors"] },
				{ id: "mechanical-engineering", name: "Mechanical Engineering", keywords: ["thermodynamics", "fluid dynamics", "manufacturing"] },
				{ id: "infrastructure", name: "Infrastructure & Systems", keywords: ["networks", "cloud computing", "data centers"] }
			]
		},
		{
			id: "business",
			name: "Business",
			description: "The practice and theory of commerce and management",
			subclasses: [
				{ id: "strategy", name: "Strategy & Management", keywords: ["competitive strategy", "leadership", "decision-making"] },
				{ id: "finance", name: "Finance & Accounting", keywords: ["corporate finance", "valuation", "capital markets"] },
				{ id: "marketing", name: "Marketing & Sales", keywords: ["branding", "digital marketing", "customer acquisition"] },
				{ id: "operations", name: "Operations & Supply Chain", keywords: ["logistics", "manufacturing", "process optimization"] },
				{ id: "economics", name: "Economics", keywords: ["microeconomics", "macroeconomics", "monetary policy"] },
				{ id: "investments", name: "Investment & Portfolio Management", keywords: ["asset allocation", "risk management", "securities"] },
				{ id: "entrepreneurship", name: "Entrepreneurship & Startups", keywords: ["venture capital", "product-market fit", "scaling"] },
				{ id: "hr-org", name: "Human Resources & Organization", keywords: ["talent management", "culture", "workforce planning"] },
				{ id: "international-business", name: "International Business & Trade", keywords: ["global markets", "trade policy", "emerging markets"] }
			]
		},
		{
			id: "geography-history",
			name: "Geography & History",
			description: "The study of places, peoples, and the past",
			subclasses: [
				{ id: "ancient-history", name: "Ancient Civilizations", keywords: ["Mesopotamia", "Egypt", "Greece", "Rome"] },
				{ id: "medieval-early-modern", name: "Medieval & Early Modern", keywords: ["feudalism", "Renaissance", "Enlightenment"] },
				{ id: "modern-contemporary", name: "Modern & Contemporary History", keywords: ["Industrial Revolution", "World Wars", "Cold War"] },
				{ id: "world-geography", name: "World Geography & Cultures", keywords: ["human geography", "demographics", "migration"] },
				{ id: "climate-environmental", name: "Climate & Environmental History", keywords: ["climate change", "sustainability"] },
				{ id: "military-political", name: "Military & Political History", keywords: ["warfare", "diplomacy", "statecraft"] },
				{ id: "economic-history", name: "Economic History", keywords: ["trade routes", "industrialization", "financial crises"] },
				{ id: "social-cultural", name: "Social & Cultural History", keywords: ["everyday life", "gender", "religion"] },
				{ id: "regional-studies", name: "Regional Studies", keywords: ["Asia", "Europe", "Americas", "Africa", "Middle East"] }
			]
		},
		{
			id: "social-sciences",
			name: "Social Sciences",
			description: "The study of human society, behavior, and thought",
			subclasses: [
				{ id: "philosophy", name: "Philosophy", keywords: ["ethics", "metaphysics", "epistemology", "logic"] },
				{ id: "psychology", name: "Psychology", keywords: ["clinical", "cognitive", "social", "developmental"] },
				{ id: "political-science", name: "Political Science & Governance", keywords: ["comparative politics", "international relations", "public policy"] },
				{ id: "sociology-anthropology", name: "Sociology & Anthropology", keywords: ["social structures", "culture", "ethnography"] },
				{ id: "linguistics", name: "Linguistics & Language", keywords: ["syntax", "semantics", "sociolinguistics"] },
				{ id: "law", name: "Law & Jurisprudence", keywords: ["constitutional", "criminal", "civil", "international law"] },
				{ id: "education", name: "Education & Pedagogy", keywords: ["curriculum", "learning theory", "instructional design"] },
				{ id: "religious-studies", name: "Religious Studies & Theology", keywords: ["world religions", "theology", "spirituality"] },
				{ id: "communication", name: "Communication & Media Studies", keywords: ["mass media", "rhetoric", "journalism"] }
			]
		},
		{
			id: "arts",
			name: "Arts",
			description: "Creative expression and aesthetic appreciation",
			subclasses: [
				{ id: "visual-arts", name: "Visual Arts", keywords: ["painting", "sculpture", "drawing"] },
				{ id: "classical-music", name: "Classical Music & Composition", keywords: ["orchestral", "opera", "music theory"] },
				{ id: "literature", name: "Literature & Poetry", keywords: ["fiction", "poetry", "drama", "literary criticism"] },
				{ id: "architecture", name: "Architecture & Design", keywords: ["architectural history", "urban design", "interior design"] },
				{ id: "film-cinema", name: "Film & Cinema", keywords: ["directing", "cinematography", "screenwriting"] },
				{ id: "theater", name: "Theater & Performing Arts", keywords: ["acting", "directing", "playwriting", "dance"] },
				{ id: "photography", name: "Photography", keywords: ["photojournalism", "portraiture", "documentary"] },
				{ id: "modern-contemporary-art", name: "Modern & Contemporary Art", keywords: ["avant-garde", "conceptual art", "digital art"] },
				{ id: "art-history", name: "Art History & Criticism", keywords: ["art movements", "aesthetics", "curation"] }
			]
		},
		{
			id: "recreation",
			name: "Recreation",
			description: "Leisure activities and entertainment",
			subclasses: [
				{ id: "team-sports", name: "Team Sports", keywords: ["football", "basketball", "soccer", "hockey"] },
				{ id: "individual-sports", name: "Individual Sports", keywords: ["tennis", "golf", "track and field", "swimming"] },
				{ id: "combat-sports", name: "Combat Sports", keywords: ["boxing", "MMA", "martial arts"] },
				{ id: "movies-television", name: "Movies & Television", keywords: ["film history", "TV series", "streaming"] },
				{ id: "video-games", name: "Video Games & Esports", keywords: ["game design", "competitive gaming"] },
				{ id: "board-games", name: "Board Games & Tabletop", keywords: ["strategy games", "RPGs", "card games"] },
				{ id: "outdoor-recreation", name: "Outdoor Recreation", keywords: ["hiking", "camping", "fishing", "mountaineering"] },
				{ id: "fitness-wellness", name: "Fitness & Wellness", keywords: ["strength training", "nutrition", "yoga"] },
				{ id: "motorsports", name: "Motorsports & Racing", keywords: ["Formula 1", "NASCAR", "rally"] }
			]
		}
	];

	// Wizard steps
	type WizardStep = 'expertise' | 'traits' | 'review';
	let currentStep: WizardStep = 'expertise';

	// State
	let botName = '';
	
	// Expertise state
	let selectedCategories: Set<string> = new Set();
	let selectedSubclasses: Set<string> = new Set();
	let expandedCategories: Set<string> = new Set();
	let customExpertise = '';
	
	// Traits state
	let traitWords: string[] = [];
	let selectedTraits: string[] = [];
	let customTraits: string[] = [];
	let customTraitInput = '';
	let isLoadingTraits = false;
	let traitRound = 1;
	let traitAnimationKey = 0;
	
	// Generation state
	let isGenerating = false;
	let generatedInstruction = '';
	let error = '';

	// Computed
	$: hasExpertise = selectedCategories.size > 0 || selectedSubclasses.size > 0 || customExpertise.trim().length > 0;
	$: totalTraits = selectedTraits.length + customTraits.length;
	$: canGenerate = botName.trim().length > 0;

	// Reset state when modal opens
	$: if (isOpen) {
		resetWizard();
	}

	function resetWizard() {
		currentStep = 'expertise';
		botName = '';
		selectedCategories = new Set();
		selectedSubclasses = new Set();
		expandedCategories = new Set();
		customExpertise = '';
		traitWords = [];
		selectedTraits = [];
		customTraits = [];
		customTraitInput = '';
		traitRound = 1;
		generatedInstruction = '';
		error = '';
	}

	// Expertise tree functions
	function toggleCategoryExpand(categoryId: string) {
		if (expandedCategories.has(categoryId)) {
			expandedCategories.delete(categoryId);
		} else {
			expandedCategories.add(categoryId);
		}
		expandedCategories = expandedCategories; // trigger reactivity
	}

	function toggleCategorySelect(categoryId: string) {
		if (selectedCategories.has(categoryId)) {
			selectedCategories.delete(categoryId);
			// Also deselect all subclasses of this category
			const category = taxonomy.find(c => c.id === categoryId);
			if (category) {
				category.subclasses.forEach(s => selectedSubclasses.delete(s.id));
				selectedSubclasses = selectedSubclasses;
			}
		} else {
			selectedCategories.add(categoryId);
			// Deselect individual subclasses since whole category is selected
			const category = taxonomy.find(c => c.id === categoryId);
			if (category) {
				category.subclasses.forEach(s => selectedSubclasses.delete(s.id));
				selectedSubclasses = selectedSubclasses;
			}
		}
		selectedCategories = selectedCategories;
	}

	function toggleSubclassSelect(categoryId: string, subclassId: string) {
		if (selectedSubclasses.has(subclassId)) {
			selectedSubclasses.delete(subclassId);
		} else {
			selectedSubclasses.add(subclassId);
			// If selecting a subclass, deselect the parent category (more specific wins)
			selectedCategories.delete(categoryId);
			selectedCategories = selectedCategories;
		}
		selectedSubclasses = selectedSubclasses;
	}

	function isSubclassDisabled(categoryId: string): boolean {
		return selectedCategories.has(categoryId);
	}

	// Trait functions
	async function fetchTraits() {
		isLoadingTraits = true;
		error = '';
		
		try {
			const response = await fetch(`${API_BASE}/wizard/words`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					selected_words: selectedTraits,
					round_number: traitRound
				})
			});

			if (!response.ok) throw new Error('Failed to load traits');

			const data = await response.json();
			traitWords = data.words;
			traitAnimationKey++;
			traitRound++;
		} catch (e) {
			console.error('Failed to fetch traits:', e);
			traitWords = [
				'analytical', 'empathetic', 'strategic', 'concise',
				'creative', 'cautious', 'bold', 'methodical',
				'pragmatic', 'visionary', 'detail-oriented', 'big-picture',
				'collaborative', 'independent', 'patient', 'decisive'
			];
			traitAnimationKey++;
		} finally {
			isLoadingTraits = false;
		}
	}

	function toggleTrait(word: string) {
		if (selectedTraits.includes(word)) {
			selectedTraits = selectedTraits.filter(w => w !== word);
		} else {
			selectedTraits = [...selectedTraits, word];
		}
	}

	function removeTrait(word: string) {
		selectedTraits = selectedTraits.filter(w => w !== word);
	}

	function addCustomTrait() {
		const word = customTraitInput.trim().toLowerCase();
		if (word && !customTraits.includes(word) && !selectedTraits.includes(word)) {
			customTraits = [...customTraits, word];
			customTraitInput = '';
		}
	}

	function removeCustomTrait(word: string) {
		customTraits = customTraits.filter(w => w !== word);
	}

	function handleCustomTraitKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			addCustomTrait();
		}
	}

	// Navigation
	function goToTraits() {
		currentStep = 'traits';
		if (traitWords.length === 0) {
			fetchTraits();
		}
	}

	function goToReview() {
		currentStep = 'review';
	}

	function goBack() {
		if (currentStep === 'traits') {
			currentStep = 'expertise';
		} else if (currentStep === 'review') {
			currentStep = 'traits';
		}
	}

	// Build expertise description for the prompt
	function buildExpertiseDescription(): string {
		const parts: string[] = [];
		
		// Full categories
		for (const catId of selectedCategories) {
			const cat = taxonomy.find(c => c.id === catId);
			if (cat) {
				parts.push(`world-class expertise across the entire domain of ${cat.name}`);
			}
		}
		
		// Individual subclasses (grouped by category for readability)
		const subclassesByCategory = new Map<string, string[]>();
		for (const subId of selectedSubclasses) {
			for (const cat of taxonomy) {
				const sub = cat.subclasses.find(s => s.id === subId);
				if (sub) {
					if (!subclassesByCategory.has(cat.name)) {
						subclassesByCategory.set(cat.name, []);
					}
					subclassesByCategory.get(cat.name)!.push(sub.name);
				}
			}
		}
		
		for (const [catName, subs] of subclassesByCategory) {
			if (subs.length === 1) {
				parts.push(`deep expertise in ${subs[0]}`);
			} else {
				parts.push(`deep expertise in ${subs.slice(0, -1).join(', ')} and ${subs[subs.length - 1]}`);
			}
		}
		
		return parts.join('; ');
	}

	// Build structured expertise for backend
	function buildExpertisePayload() {
		const categories: string[] = [];
		const subclasses: { category: string; subclass: string }[] = [];
		
		for (const catId of selectedCategories) {
			const cat = taxonomy.find(c => c.id === catId);
			if (cat) categories.push(cat.name);
		}
		
		for (const subId of selectedSubclasses) {
			for (const cat of taxonomy) {
				const sub = cat.subclasses.find(s => s.id === subId);
				if (sub) {
					subclasses.push({ category: cat.name, subclass: sub.name });
				}
			}
		}
		
		return { categories, subclasses };
	}

	async function generatePersona() {
		if (!canGenerate) return;
		
		isGenerating = true;
		error = '';

		try {
			const expertise = buildExpertisePayload();
			
			const response = await fetch(`${API_BASE}/wizard/generate`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					name: botName.trim(),
					selected_words: selectedTraits,
					custom_words: customTraits,
					expertise_categories: expertise.categories,
					expertise_subclasses: expertise.subclasses,
					custom_expertise: customExpertise.trim() || null
				})
			});

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || 'Failed to generate persona');
			}

			const data = await response.json();
			generatedInstruction = data.instruction;
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
		generatedInstruction = '';
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
			handleClose();
		}
	}

	// Get display summary of selections
	function getExpertiseSummary(): { categories: string[]; subclasses: string[]; custom: string } {
		const categories: string[] = [];
		const subclasses: string[] = [];
		
		for (const catId of selectedCategories) {
			const cat = taxonomy.find(c => c.id === catId);
			if (cat) categories.push(cat.name);
		}
		
		for (const subId of selectedSubclasses) {
			for (const cat of taxonomy) {
				const sub = cat.subclasses.find(s => s.id === subId);
				if (sub) subclasses.push(sub.name);
			}
		}
		
		return { categories, subclasses, custom: customExpertise.trim() };
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
						<h2 id="wizard-title" class="text-xl font-bold text-gray-900 dark:text-white">Bot Wizard</h2>
						<p class="text-sm text-gray-500 dark:text-gray-400">
							{#if currentStep === 'expertise'}
								Step 1: Choose areas of expertise
							{:else if currentStep === 'traits'}
								Step 2: Select personality traits
							{:else}
								Step 3: Review and generate
							{/if}
						</p>
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

			<!-- Step Indicator -->
			<div class="px-6 py-3 bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-700">
				<div class="flex items-center gap-2">
					<div class="flex items-center gap-2">
						<div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium {currentStep === 'expertise' ? 'bg-blue-600 text-white' : 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400'}">1</div>
						<span class="text-sm {currentStep === 'expertise' ? 'text-gray-900 dark:text-white font-medium' : 'text-gray-500 dark:text-gray-400'}">Expertise</span>
					</div>
					<div class="flex-1 h-px bg-gray-300 dark:bg-gray-600"></div>
					<div class="flex items-center gap-2">
						<div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium {currentStep === 'traits' ? 'bg-blue-600 text-white' : currentStep === 'review' ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400' : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'}">2</div>
						<span class="text-sm {currentStep === 'traits' ? 'text-gray-900 dark:text-white font-medium' : 'text-gray-500 dark:text-gray-400'}">Traits</span>
					</div>
					<div class="flex-1 h-px bg-gray-300 dark:bg-gray-600"></div>
					<div class="flex items-center gap-2">
						<div class="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium {currentStep === 'review' ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400'}">3</div>
						<span class="text-sm {currentStep === 'review' ? 'text-gray-900 dark:text-white font-medium' : 'text-gray-500 dark:text-gray-400'}">Review</span>
					</div>
				</div>
			</div>

			<!-- Content -->
			<div class="flex-1 overflow-y-auto p-6">
				{#if currentStep === 'expertise'}
					<!-- STEP 1: Expertise Tree -->
					<div transition:fly={{ x: -20, duration: 200 }}>
						<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
							Select areas where your advisor has world-class expertise. Check a category for broad knowledge, or expand to pick specific subfields.
						</p>
						
						<div class="space-y-1">
							{#each taxonomy as category (category.id)}
								<div class="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
									<!-- Category Header -->
									<div class="flex items-center gap-2 px-3 py-2 bg-gray-50 dark:bg-gray-800">
										<!-- Checkbox -->
										<button
											on:click={() => toggleCategorySelect(category.id)}
											class="w-5 h-5 rounded border-2 flex items-center justify-center transition {selectedCategories.has(category.id) 
												? 'bg-blue-600 border-blue-600 text-white' 
												: 'border-gray-300 dark:border-gray-600 hover:border-blue-500'}"
										>
											{#if selectedCategories.has(category.id)}
												<svg class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
												</svg>
											{/if}
										</button>
										
										<!-- Expand/Collapse + Name -->
										<button
											on:click={() => toggleCategoryExpand(category.id)}
											class="flex-1 flex items-center gap-2 text-left"
										>
											<svg 
												class="w-4 h-4 text-gray-500 transition-transform {expandedCategories.has(category.id) ? 'rotate-90' : ''}" 
												fill="none" 
												stroke="currentColor" 
												viewBox="0 0 24 24"
											>
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
											</svg>
											<span class="font-medium text-gray-900 dark:text-white">{category.name}</span>
											{#if selectedCategories.has(category.id)}
												<span class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400">All</span>
											{:else}
												{@const selectedCount = category.subclasses.filter(s => selectedSubclasses.has(s.id)).length}
												{#if selectedCount > 0}
													<span class="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400">{selectedCount}</span>
												{/if}
											{/if}
										</button>
									</div>
									
									<!-- Subclasses -->
									{#if expandedCategories.has(category.id)}
										<div class="px-3 py-2 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700" transition:slide={{ duration: 150 }}>
											<div class="grid grid-cols-2 gap-1 pl-7">
												{#each category.subclasses as subclass (subclass.id)}
													<button
														on:click={() => toggleSubclassSelect(category.id, subclass.id)}
														disabled={isSubclassDisabled(category.id)}
														class="flex items-center gap-2 px-2 py-1.5 rounded text-left text-sm transition {isSubclassDisabled(category.id)
															? 'opacity-50 cursor-not-allowed'
															: selectedSubclasses.has(subclass.id)
																? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300'
																: 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'}"
													>
														<div class="w-4 h-4 rounded border flex items-center justify-center {selectedSubclasses.has(subclass.id) ? 'bg-blue-600 border-blue-600 text-white' : 'border-gray-300 dark:border-gray-600'}">
															{#if selectedSubclasses.has(subclass.id)}
																<svg class="w-2.5 h-2.5" fill="none" stroke="currentColor" stroke-width="3" viewBox="0 0 24 24">
																	<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
																</svg>
															{/if}
														</div>
														<span class="truncate">{subclass.name}</span>
													</button>
												{/each}
											</div>
										</div>
									{/if}
								</div>
							{/each}
						</div>
						
						<!-- Custom Expertise Input -->
						<div class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
							<label for="custom-expertise" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
								Or describe your own expertise
							</label>
							<textarea
								id="custom-expertise"
								bind:value={customExpertise}
								placeholder="e.g., 20 years of experience brewing craft beer with expertise in Belgian styles, hop chemistry, and scaling microbrewery operations..."
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition resize-none"
								rows="3"
							></textarea>
							<p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
								Describe any specialized knowledge, skills, or experience. botchat will expand this into detailed expertise.
							</p>
						</div>
					</div>
				{:else if currentStep === 'traits'}
					<!-- STEP 2: Traits -->
					<div transition:fly={{ x: 20, duration: 200 }}>
						<!-- Selected Traits Pills -->
						{#if selectedTraits.length > 0 || customTraits.length > 0}
							<div class="mb-4" transition:fly={{ y: -10, duration: 200 }}>
								<p class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
									Selected traits ({totalTraits})
								</p>
								<div class="flex flex-wrap gap-2">
									{#each selectedTraits as word (word)}
										<button
											on:click={() => removeTrait(word)}
											class="px-3 py-1.5 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded-full text-sm font-medium flex items-center gap-1.5 hover:bg-blue-200 dark:hover:bg-blue-900 transition group"
											transition:scale={{ duration: 150 }}
										>
											{word}
											<svg class="w-3.5 h-3.5 opacity-50 group-hover:opacity-100" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
											</svg>
										</button>
									{/each}
									{#each customTraits as word (word)}
										<button
											on:click={() => removeCustomTrait(word)}
											class="px-3 py-1.5 bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300 rounded-full text-sm font-medium flex items-center gap-1.5 hover:bg-green-200 dark:hover:bg-green-900 transition group"
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

						<!-- Trait Grid -->
						<div class="mb-4">
							<div class="flex items-center justify-between mb-3">
								<p class="text-sm text-gray-600 dark:text-gray-400">
									Select traits that define personality and style
								</p>
								<button
									on:click={fetchTraits}
									disabled={isLoadingTraits}
									class="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition disabled:opacity-50"
								>
									<svg 
										class="w-4 h-4 {isLoadingTraits ? 'animate-spin' : ''}" 
										fill="none" 
										stroke="currentColor" 
										viewBox="0 0 24 24"
									>
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
									</svg>
									Refresh
								</button>
							</div>

							{#key traitAnimationKey}
								<div class="grid grid-cols-4 gap-2">
									{#each traitWords as word, i (word + '-' + i)}
										<button
											on:click={() => toggleTrait(word)}
											disabled={selectedTraits.includes(word)}
											class="px-3 py-2.5 text-sm font-medium rounded-xl transition-all duration-200 {selectedTraits.includes(word) 
												? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30 scale-95' 
												: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 hover:scale-[1.02]'}"
											in:fly={{ y: 10, duration: 200, delay: i * 30 }}
										>
											{word}
										</button>
									{/each}
								</div>
							{/key}
						</div>

						<!-- Custom Trait Input -->
						<div>
							<label for="custom-trait" class="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-2 uppercase tracking-wider">
								Add your own
							</label>
							<div class="flex gap-2">
								<input
									id="custom-trait"
									type="text"
									bind:value={customTraitInput}
									on:keydown={handleCustomTraitKeydown}
									placeholder="Type a trait and press Enter..."
									class="flex-1 px-4 py-2 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
								/>
								<button
									on:click={addCustomTrait}
									disabled={!customTraitInput.trim()}
									class="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl hover:bg-gray-300 dark:hover:bg-gray-600 transition disabled:opacity-50 disabled:cursor-not-allowed"
								>
									Add
								</button>
							</div>
						</div>
					</div>
				{:else if currentStep === 'review'}
					<!-- STEP 3: Review -->
					<div transition:fly={{ x: 20, duration: 200 }}>
						{#if generatedInstruction}
							<!-- Generated Preview -->
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
						{:else}
							<!-- Review Before Generate -->
							<!-- Name Input -->
							<div class="mb-6">
								<label for="bot-name" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
									Name your bot
								</label>
								<input
									id="bot-name"
									type="text"
									bind:value={botName}
									placeholder="e.g., Catherine, Marcus, The Strategist..."
									class="w-full px-4 py-3 bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
								/>
							</div>

							<!-- Expertise Summary -->
							{@const summary = getExpertiseSummary()}
							<div class="mb-4">
								<div class="flex items-center justify-between mb-2">
									<p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
										Expertise
									</p>
									<button
										on:click={() => currentStep = 'expertise'}
										class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
									>
										Edit
									</button>
								</div>
								<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
										{#if summary.categories.length === 0 && summary.subclasses.length === 0 && !summary.custom}
											<p class="text-sm text-gray-500 dark:text-gray-400 italic">No expertise selected (traits-only bot)</p>
										{:else}
											<div class="flex flex-wrap gap-2">
												{#each summary.categories as cat}
													<span class="px-2 py-1 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded text-xs font-medium">
														{cat} (all)
													</span>
												{/each}
												{#each summary.subclasses as sub}
													<span class="px-2 py-1 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded text-xs">
														{sub}
													</span>
												{/each}
											</div>
											{#if summary.custom}
												<div class="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700">
													<p class="text-xs text-gray-500 dark:text-gray-400 mb-1">Custom:</p>
													<p class="text-sm text-gray-700 dark:text-gray-300 italic">{summary.custom}</p>
												</div>
											{/if}
									{/if}
								</div>
							</div>

							<!-- Traits Summary -->
							<div class="mb-6">
								<div class="flex items-center justify-between mb-2">
									<p class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
										Personality Traits
									</p>
									<button
										on:click={() => currentStep = 'traits'}
										class="text-xs text-blue-600 dark:text-blue-400 hover:underline"
									>
										Edit
									</button>
								</div>
								<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
									{#if totalTraits === 0}
										<p class="text-sm text-gray-500 dark:text-gray-400 italic">No traits selected</p>
									{:else}
										<div class="flex flex-wrap gap-2">
											{#each selectedTraits as trait}
												<span class="px-2 py-1 bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 rounded text-xs">
													{trait}
												</span>
											{/each}
											{#each customTraits as trait}
												<span class="px-2 py-1 bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300 rounded text-xs">
													{trait}
												</span>
											{/each}
										</div>
									{/if}
								</div>
							</div>

							{#if error}
								<div class="mb-4 p-3 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg text-sm">
									{error}
								</div>
							{/if}
						{/if}
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
				<div class="flex items-center justify-between">
					{#if currentStep === 'expertise'}
						<p class="text-sm text-gray-500 dark:text-gray-400">
							{#if hasExpertise}
								{selectedCategories.size + selectedSubclasses.size} area{selectedCategories.size + selectedSubclasses.size !== 1 ? 's' : ''} selected
							{:else}
								Select expertise or skip to traits
							{/if}
						</p>
						<button
							on:click={goToTraits}
							class="px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl font-medium transition-all hover:from-blue-600 hover:to-blue-700 shadow-lg shadow-blue-500/25 flex items-center gap-2"
						>
							{hasExpertise ? 'Next: Traits' : 'Skip to Traits'}
							<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
							</svg>
						</button>
					{:else if currentStep === 'traits'}
						<button
							on:click={goBack}
							class="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition"
						>
							← Back
						</button>
						<button
							on:click={goToReview}
							class="px-6 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl font-medium transition-all hover:from-blue-600 hover:to-blue-700 shadow-lg shadow-blue-500/25 flex items-center gap-2"
						>
							{totalTraits > 0 ? 'Next: Review' : 'Skip to Review'}
							<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
							</svg>
						</button>
					{:else if currentStep === 'review' && !generatedInstruction}
						<button
							on:click={goBack}
							class="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition"
						>
							← Back
						</button>
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
					{:else}
						<div></div>
						<div></div>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}
