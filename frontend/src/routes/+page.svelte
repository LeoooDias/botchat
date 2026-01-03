<script lang="ts">
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import BotLibrary from '$lib/components/BotLibrary.svelte';
	import NewBotForm from '$lib/components/NewBotForm.svelte';
	import GlobalAttachment from '$lib/components/GlobalAttachment.svelte';
	import ChatMessages from '$lib/components/ChatMessages.svelte';
	import MessageInput from '$lib/components/MessageInput.svelte';
	import SettingsModal from '$lib/components/SettingsModal.svelte';
	import SummarizeModal from '$lib/components/SummarizeModal.svelte';
	import SummaryResultModal from '$lib/components/SummaryResultModal.svelte';
	import LoginButton from '$lib/components/LoginButton.svelte';
	import SignInModal from '$lib/components/SignInModal.svelte';
	import AboutModal from '$lib/components/AboutModal.svelte';
	import AlertModal from '$lib/components/AlertModal.svelte';
	import IntroModal from '$lib/components/IntroModal.svelte';
	import EditBotDialog from '$lib/components/EditBotDialog.svelte';
	// Mobile components
	import MobileNav from '$lib/components/MobileNav.svelte';
	import MobileHeader from '$lib/components/MobileHeader.svelte';
	import SlidePanel from '$lib/components/SlidePanel.svelte';
	import MobileConversationList from '$lib/components/MobileConversationList.svelte';
	import MobileActiveBots from '$lib/components/MobileActiveBots.svelte';
	import { auth, isAuthenticated, isSessionValid, authToken, getAuthHeaders, authLoading, logout } from '$lib/stores/auth';
	import { subscription, quota, tierLimits, isPaidUser, tierName, quotaStatus, isQuotaExhausted, quotaPercentage } from '$lib/stores/subscription';
	import { providersStore, configuredProviderIds, getProviderDisplayName } from '$lib/stores/providers';
	import { getContextWindow, isBotModelValid, validateBotModel } from '$lib/modelLimits';
	import { getProviderKey, getConfiguredProviders, validateEncryptionKey } from '$lib/utils/keyEncryption';
	import { getUserItem, setUserItem, removeUserItem, getGlobalItem, setGlobalItem, migrateUserData } from '$lib/utils/userStorage';
	import { needsStarterConfig, getStarterBots, buildStarterConversation, STARTER_MESSAGE, type StarterBot } from '$lib/starterConfig';

	// Alert modal state
	let alertOpen = false;
	let alertTitle = '';
	let alertMessage = '';
	let alertType: 'info' | 'warning' | 'error' | 'success' = 'info';

	function showAlert(title: string, message: string, type: 'info' | 'warning' | 'error' | 'success' = 'info') {
		alertTitle = title;
		alertMessage = message;
		alertType = type;
		alertOpen = true;
	}

	interface Message {
		id: string;
		role: 'user' | 'assistant';
		content: string;
		timestamp: number;
		botId?: string;
		provider?: string;
		model?: string;
		isError?: boolean;
		isTruncated?: boolean; // Response was cut off due to max_tokens limit
		finishReason?: string; // Raw finish_reason from provider
		lastInputs?: {
			message: string;
			attachments: File[];
		};
	}

	interface Bot {
		id: string;
		provider: string;
		model: string;
		systemInstructionFile?: File;
		systemInstructionText?: string;
		name?: string;
		maxTokens?: number;
		category?: string;
	}

	let messages: Message[] = [];
	let conversationMessages: { [convId: string]: Message[] } = {}; // Per-conversation message storage (persisted to sessionStorage)
	let bots: Bot[] = []; // User library of bots
	let globalAttachments: File[] = [];
	let hasOversizedAttachments = false; // Track if any attachment exceeds 50MB limit
	let currentInputMessage = ''; // Current message being typed (for token estimation)
	let isLoading = false;

	// Estimate INPUT tokens for a specific bot (what we're sending, not including response)
	function estimateTokensForBot(bot: Bot, inputMessage: string): number {
		// Rough token estimation: ~4 characters per token
		let totalText = '';

		// Add system instruction for this bot
		const systemInstructionLength = bot.systemInstructionText?.length || 0;

		// Add conversation history
		for (const msg of messages) {
			totalText += msg.content + ' ';
		}

		// Add attachment tokens (estimate ~1 token per 4000 bytes, plus base tokens per file)
		let attachmentTokens = 0;
		for (const file of globalAttachments) {
			attachmentTokens += Math.ceil(file.size / 4000) + 50;
		}

		// Add current message
		totalText += inputMessage;

		// Input tokens only = system + history + message + attachments
		return Math.ceil(systemInstructionLength / 4) + Math.ceil(totalText.length / 4) + attachmentTokens;
	}

	let sidebarOpen = true; // Sidebar visibility state
	let currentStreamingMessageIds = new Map<string, string>(); // Maps config_id to message.id for active streams
	let streamingCount = 0; // Reactive counter for active streams (since Map.size isn't reactive)
	let settingsOpen = false; // Settings modal state
	let signInOpen = false; // Sign-in modal state
	let aboutOpen = false; // About modal state
	let introOpen = false; // Intro modal state (for new users)
	let editBotDialogOpen = false; // Edit active bot dialog state
	let editingActiveBot: Bot | null = null; // Bot being edited in the dialog
	let theme: 'light' | 'dark' = 'light'; // Theme state
	let summarizeOpen = false; // Summarize modal state
	let isSummarizing = false; // Summarization in progress
	let summaryResultOpen = false; // Summary result modal state
	let summaryContent = ''; // Summary content
	let selectedSummaryBot: Bot | null = null; // Selected bot for summary
	let currentRunAbortController: AbortController | null = null; // For cancelling in-flight requests
	let removeAllConfirmOpen = false; // Remove all bots confirmation modal
	let newBotFormOpen = true; // New Bot Form collapsible state
	let attachmentsOpen = true; // Attachments section collapsible state
	let clearConvConfirmOpen = false; // Clear conversation confirmation modal
	let closeChatConfirmOpen = false; // Close chat confirmation modal
	let chatToClose: string | null = null; // ID of chat pending close confirmation
	let duplicateNameErrorOpen = false; // Duplicate conversation name error modal
	let exportModalOpen = false; // Export options modal
	let importConfirmOpen = false; // Import confirmation modal
	let importResultOpen = false; // Import result modal
	let pendingImportConfig: { bots: Bot[]; conversations: Conversation[]; categories?: any[]; settings?: { theme?: string } } | null = null; // Config to be imported
	let importResultSuccess = false; // Whether import was successful
	let importResultMessage = ''; // Import result message
	let globalMaxTokens = 4000; // Global max tokens default for all API calls

	// Mobile UI state
	let isMobile = false; // Reactive: true when viewport is mobile-sized
	let mobilePanel: 'none' | 'library' | 'chats' | 'newbot' | 'attachments' = 'none'; // Currently open mobile panel
	let mobileActionsOpen = false; // Mobile chat actions bottom sheet

	// Conversation management
	type ResponseModifier = 'none' | 'chat' | 'deep';

	// Provider color coding for active bot chips
	const PROVIDER_COLORS: Record<string, { bg: string; border: string; text: string; subtext: string }> = {
		'openai': {
			bg: 'bg-green-100 dark:bg-green-900/40',
			border: 'border-green-300 dark:border-green-700',
			text: 'text-green-900 dark:text-green-100',
			subtext: 'text-green-700 dark:text-green-300'
		},
		'anthropic': {
			bg: 'bg-orange-100 dark:bg-orange-900/40',
			border: 'border-orange-300 dark:border-orange-700',
			text: 'text-orange-900 dark:text-orange-100',
			subtext: 'text-orange-700 dark:text-orange-300'
		},
		'gemini': {
			bg: 'bg-blue-100 dark:bg-blue-900/40',
			border: 'border-blue-300 dark:border-blue-700',
			text: 'text-blue-900 dark:text-blue-100',
			subtext: 'text-blue-700 dark:text-blue-300'
		}
	};

	const DEFAULT_PROVIDER_COLOR = {
		bg: 'bg-gray-100 dark:bg-gray-700',
		border: 'border-gray-300 dark:border-gray-600',
		text: 'text-gray-900 dark:text-gray-100',
		subtext: 'text-gray-700 dark:text-gray-300'
	};

	function getProviderColor(provider: string) {
		return PROVIDER_COLORS[provider.toLowerCase()] || DEFAULT_PROVIDER_COLOR;
	}

	interface Conversation {
		id: string;
		name: string;
		description: string;
		activeBots: Bot[];
		activeBotsExpanded: boolean;
		createdAt: number;
		isPrivate: boolean;
		responseModifier?: ResponseModifier;
	}

	// Response modifier prompts
	const CHAT_MODIFIER = `
--
Response Length Mode: CHAT (brief, chat-style).
	•	Keep the response short and conversational.
	•	Default to 3–7 bullet points or 2–5 short paragraphs max.
	•	Lead with the answer / recommendation first (no long preamble).
	•	Focus on the highest-leverage 1–3 ideas only; omit nice-to-haves.
	•	Use plain language, minimal jargon.
	•	If the request is broad/ambiguous, make reasonable assumptions and proceed; ask at most 1 clarifying question only if truly blocking.
	•	Avoid long lists, exhaustive coverage, and multi-section reports unless explicitly asked.
	•	If you reference steps, keep it to a tight checklist (max ~7 steps).
	•	Target ~150–300 words unless the user explicitly asks for more.`;

	const DEEP_MODIFIER = `
--
Response Length Mode: DEPTH (deep, comprehensive analysis).
	•	Provide a thorough, structured response with clear headings.
	•	Start with a crisp executive summary (3–8 bullets), then expand.
	•	Cover: context → key considerations → tradeoffs → recommended approach → implementation steps → risks & mitigations → alternatives.
	•	Be explicit about assumptions and note what would change the recommendation.
	•	Prefer complete reasoning over brevity; include useful detail, examples, and edge cases when relevant.
	•	Offer at least one practical template/checklist the user can reuse.
	•	If information is missing, ask up to 3 targeted clarifying questions, but still provide a best-effort answer in the meantime.
	•	When giving steps, include sequencing, prerequisites, and "definition of done."
	•	Target ~800–1500 words unless the user requests otherwise.`;

	let conversations: Conversation[] = [];
	let currentConversationId: string = '';

	// Conversation UI state
	let draggedConvId: string | null = null;
	let renamingConvId: string | null = null;
	let renameInputValue: string = '';
	let editingDescriptionId: string | null = null;
	let dropIndicatorIndex: number | null = null;
	let dragOverSide: 'left' | 'right' | null = null;

	// Derived reactive values
	$: currentConversation = conversations.find(c => c.id === currentConversationId);
	$: activeBots = currentConversation?.activeBots || [];
	$: activeBotsExpanded = currentConversation?.activeBotsExpanded ?? true;
	$: isStreaming = streamingCount > 0;  // True when responses are streaming in
	
	// Check if any active bot has an invalid model (for disabling Send button)
	$: hasInvalidActiveBots = activeBots.some(bot => !isBotModelValid(bot));
	$: invalidActiveBotsCount = activeBots.filter(bot => !isBotModelValid(bot)).length;
	
	// Fetch subscription status, quota, and provider config when auth state changes
	$: if ($isAuthenticated) {
		subscription.fetchStatus();
		quota.fetchQuota();
		loadProviderConfig();
	} else {
		subscription.reset();
		quota.reset();
		providersStore.reset();
		clearEncryptionKeyCache();  // Clear cached encryption key on sign out
	}

	// Tier limit checks (reactive)
	$: canCreateConversation = conversations.length < $tierLimits.maxConversations;
	$: canSaveBot = bots.length < $tierLimits.maxSavedBots;
	$: canAddBotToConversation = activeBots.length < $tierLimits.maxBotsPerConversation;

	// Extract bots that participated in the conversation from messages
	$: participatingBots = (() => {
		const botsMap = new Map<string, Bot>();
		for (const msg of messages) {
			if (msg.role !== 'user' && msg.provider && msg.model && msg.botId) {
				// Use botId as key to avoid deduplicating bots with same provider/model
				if (!botsMap.has(msg.botId)) {
					// Look up bot name from activeBots
					const activeBot = activeBots.find(b => b.id === msg.botId);
					botsMap.set(msg.botId, {
						id: msg.botId,
						name: activeBot?.name,
						provider: msg.provider,
						model: msg.model
					});
				}
			}
		}
		return Array.from(botsMap.values()).sort((a, b) => 
			(a.name || a.model).localeCompare(b.name || b.model)
		);
	})();

	// API base URL - configure via VITE_API_BASE environment variable for production
	// Development: http://localhost:8000 (default)
	// Production: https://api.yourdomain.com
	const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
	const API_KEY = import.meta.env.VITE_API_KEY || '';
	
	// Cached encryption key for client-side API key decryption
	let cachedEncryptionKey: string | null = null;

	function authHeaders(): Record<string, string> {
		// Prefer JWT from auth store if authenticated
		const jwtHeaders = getAuthHeaders();
		if (jwtHeaders.Authorization) {
			return jwtHeaders;
		}
		// Fall back to static API key (for dev/self-hosted)
		return API_KEY ? { 'x-api-key': API_KEY } : {};
	}
	
	// Fetch and cache the encryption key from the server
	async function getEncryptionKey(): Promise<string | null> {
		if (cachedEncryptionKey) return cachedEncryptionKey;
		
		try {
			const headers = authHeaders();
			console.log('[BYOK] Fetching encryption key, auth headers present:', !!headers.Authorization);
			
			const response = await fetch(`${API_BASE}/auth/encryption-key`, {
				credentials: 'include',
				headers
			});
			
			if (response.ok) {
				const data = await response.json();
				cachedEncryptionKey = data.encryption_key;
				console.log('[BYOK] Encryption key fetched successfully');
				
				// Validate that this encryption key matches what was used to encrypt localStorage keys
				// If different (e.g., user account changed), clear stale keys
				const keysValid = await validateEncryptionKey(cachedEncryptionKey);
				if (!keysValid) {
					console.warn('[BYOK] Stale keys cleared - user will need to re-enter API keys');
					// Refresh provider config to reflect cleared keys
					await loadProviderConfig();
				}
				
				return cachedEncryptionKey;
			} else {
				const errorText = await response.text();
				console.error('[BYOK] Failed to fetch encryption key:', response.status, errorText);
			}
		} catch (e) {
			console.error('[BYOK] Exception fetching encryption key:', e);
		}
		return null;
	}
	
	// Clear cached encryption key on sign out
	function clearEncryptionKeyCache() {
		cachedEncryptionKey = null;
	}

	// Provider configuration management
	async function loadProviderConfig() {
		try {
			await providersStore.load(API_BASE, authHeaders);
		} catch (e) {
			console.error('Failed to load provider configuration:', e);
		}
	}

	// Calculate how many bots use each provider (for warning when removing keys)
	$: botCountsByProvider = (() => {
		const counts: Record<string, number> = {};
		// Count saved bots
		for (const bot of bots) {
			counts[bot.provider] = (counts[bot.provider] || 0) + 1;
		}
		// Count active bots (may overlap with saved)
		for (const bot of activeBots) {
			if (!bots.find(b => b.id === bot.id)) {
				counts[bot.provider] = (counts[bot.provider] || 0) + 1;
			}
		}
		return counts;
	})();

	// Remove all bots using a specific provider
	function removeBotsForProvider(providerId: string) {
		// Remove from saved bots
		const removedBots = bots.filter(b => b.provider === providerId);
		bots = bots.filter(b => b.provider !== providerId);
		setUserItem('savedBots', JSON.stringify(bots));

		// Remove from active bots in current conversation
		activeBots = activeBots.filter(b => b.provider !== providerId);

		// Clean up messages from removed bots in current conversation
		const removedBotIds = new Set(removedBots.map(b => b.id));
		messages = messages.filter(m => !m.botId || !removedBotIds.has(m.botId));

		// Also clean up in all stored conversations
		for (const [convId, convMessages] of Object.entries(conversationMessages)) {
			conversationMessages[convId] = convMessages.filter(m => !m.botId || !removedBotIds.has(m.botId));
		}

		// Update conversations in localStorage (remove bots from each conversation)
		if (currentConversation) {
			const updatedConversations = conversations.map(conv => ({
				...conv,
				activeBots: conv.activeBots?.filter((b: Bot) => b.provider !== providerId) || []
			}));
			setUserItem('conversations', JSON.stringify(updatedConversations));
			conversations = updatedConversations;

			// Update current conversation's active bots
			if (currentConversation.activeBots) {
				currentConversation = {
					...currentConversation,
					activeBots: currentConversation.activeBots.filter((b: Bot) => b.provider !== providerId)
				};
			}
		}

		return removedBots.length;
	}

	// Theme management
	function applyTheme(newTheme: 'light' | 'dark') {
		if (newTheme === 'dark') {
			document.documentElement.classList.add('dark');
		} else {
			document.documentElement.classList.remove('dark');
		}
	}

	function handleThemeChange(newTheme: 'light' | 'dark') {
		theme = newTheme;
		setGlobalItem('theme', newTheme);
		applyTheme(newTheme);
	}

	// Persist settings to localStorage (only in browser)
	$: if (browser && $isAuthenticated) setUserItem('globalMaxTokens', JSON.stringify(globalMaxTokens));

	// Persist conversation changes to localStorage
	$: if (browser && currentConversation && $isAuthenticated) {
		setUserItem('conversations', JSON.stringify(conversations));
	}

	// Persist messages to sessionStorage when they change (survives page navigation)
	$: if (browser && currentConversationId && messages) {
		saveMessages();
	}

	// Helper function to read file content
	async function readFileContent(file: File): Promise<string> {
		return new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = () => resolve(reader.result as string);
			reader.onerror = () => reject(new Error(`Failed to read file: ${file.name}`));
			reader.readAsText(file);
		});
	}

	// Conversation management functions
	function createNewConversation() {
		// Prevent creating new conversation while responses are streaming
		if (streamingCount > 0) {
			return;
		}
		
		// Check tier limits
		if (!canCreateConversation) {
			showAlert('Chat Limit Reached', `Free tier limit: ${$tierLimits.maxConversations} chats maximum.\n\nSubscribe for unlimited chats!`, 'warning');
			return;
		}
		
		// Save current conversation's messages before creating new one
		if (currentConversationId) {
			conversationMessages[currentConversationId] = messages;
		}
		
		const id = `conv_${Date.now()}`;
		const newConversation: Conversation = {
			id,
			name: `Chat ${conversations.length + 1}`,
			description: '',
			activeBots: [],
			activeBotsExpanded: true,
			createdAt: Date.now(),
			isPrivate: false
		};
		conversations = [...conversations, newConversation];
		currentConversationId = id;
		conversationMessages[id] = []; // Initialize empty message storage for new conversation
		messages = [];
		saveConversations();
	}

	function switchConversation(conversationId: string) {
		if (currentConversationId === conversationId) return;
		// Save current messages before switching
		saveMessages();
		currentConversationId = conversationId;
		// Load messages for the new conversation
		messages = conversationMessages[conversationId] || [];
		saveConversations();
	}

	function confirmCloseChat(conversationId: string) {
		const conv = conversations.find(c => c.id === conversationId);
		const convMessages = conversationMessages[conversationId] || [];
		const hasMessages = convMessages.length > 0;
		const hasBots = conv?.activeBots && conv.activeBots.length > 0;
		
		if (hasMessages || hasBots) {
			// Show confirmation modal
			chatToClose = conversationId;
			closeChatConfirmOpen = true;
		} else {
			// No messages or bots, delete directly
			deleteConversation(conversationId);
		}
	}

	function executeCloseChat() {
		if (chatToClose) {
			deleteConversation(chatToClose);
			chatToClose = null;
		}
		closeChatConfirmOpen = false;
	}

	function cancelCloseChat() {
		chatToClose = null;
		closeChatConfirmOpen = false;
	}

	function deleteConversation(conversationId: string) {
		// Clear messages for this conversation from sessionStorage
		clearConversationMessages(conversationId);
		conversations = conversations.filter(c => c.id !== conversationId);
		if (currentConversationId === conversationId) {
			if (conversations.length > 0) {
				currentConversationId = conversations[0].id;
				messages = conversationMessages[currentConversationId] || [];
			} else {
				createNewConversation();
			}
		}
		saveConversations();
	}

	function renameConversation(conversationId: string, newName: string) {
		const conv = conversations.find(c => c.id === conversationId);
		if (conv) {
			conv.name = newName;
			conversations = conversations;
			saveConversations();
		}
	}

	function saveConversations() {
		if (browser && $isAuthenticated) {
			setUserItem('conversations', JSON.stringify(conversations));
			setUserItem('currentConversationId', currentConversationId);
		}
	}

	// Save messages to sessionStorage (survives page navigation but not tab close)
	function saveMessages() {
		if (browser && currentConversationId) {
			// Save current conversation messages to the in-memory store
			conversationMessages[currentConversationId] = messages;
			// Persist all conversation messages to sessionStorage
			try {
				const messagesData = JSON.stringify(conversationMessages);
				sessionStorage.setItem('conversationMessages', messagesData);
			} catch (e) {
				// sessionStorage might be full or unavailable
				console.warn('Failed to save messages to sessionStorage:', e);
			}
		}
	}

	// Load messages from sessionStorage
	function loadMessages() {
		if (browser) {
			try {
				const saved = sessionStorage.getItem('conversationMessages');
				if (saved) {
					conversationMessages = JSON.parse(saved);
					// Load messages for current conversation
					if (currentConversationId && conversationMessages[currentConversationId]) {
						messages = conversationMessages[currentConversationId];
					}
				}
			} catch (e) {
				console.warn('Failed to load messages from sessionStorage:', e);
			}
		}
	}

	// Clear messages for a specific conversation from sessionStorage
	function clearConversationMessages(conversationId: string) {
		delete conversationMessages[conversationId];
		if (browser) {
			try {
				sessionStorage.setItem('conversationMessages', JSON.stringify(conversationMessages));
			} catch (e) {
				console.warn('Failed to update sessionStorage:', e);
			}
		}
	}

	function loadConversations() {
		if (browser && $isAuthenticated) {
			const saved = getUserItem('conversations');
			if (saved) {
				try {
					conversations = JSON.parse(saved);
				} catch (e) {
					console.error('Failed to load conversations:', e);
				}
			}
			
			const savedCurrentId = getUserItem('currentConversationId');
			if (savedCurrentId && conversations.find(c => c.id === savedCurrentId)) {
				currentConversationId = savedCurrentId;
			} else if (conversations.length > 0) {
				currentConversationId = conversations[0].id;
			} else {
				// Check if this is a truly new user (never initialized before)
				const initialized = getUserItem('starterConfigInitialized');
				if (needsStarterConfig(initialized)) {
					initializeStarterConfig();
				} else {
					// Create initial conversation if none exist
					createNewConversation();
				}
			}
		}
	}

	/**
	 * Initialize starter configuration for new users.
	 * Creates "The Decision Makers" bots and a sample conversation with pre-loaded question.
	 */
	function initializeStarterConfig() {
		// Mark as initialized FIRST to prevent re-running even if something fails
		setUserItem('starterConfigInitialized', 'true');
		
		// Get starter bots
		const starterBots = getStarterBots();
		
		// Add starter bots to the user's bot library
		bots = starterBots.map(b => ({
			id: b.id,
			provider: b.provider,
			model: b.model,
			name: b.name,
			systemInstructionText: b.systemInstructionText,
			category: b.category
		}));
		
		// Save bots to localStorage
		const serializable = bots.map((b) => ({
			id: b.id,
			provider: b.provider,
			model: b.model,
			systemInstructionText: b.systemInstructionText,
			name: b.name,
			maxTokens: b.maxTokens,
			category: b.category
		}));
		setUserItem('savedBots', JSON.stringify(serializable));
		
		// Save the "Decision Makers" category
		const categories = [{ name: 'Decision Makers', expanded: true }];
		setUserItem('botCategories', JSON.stringify(categories));
		
		// Create starter conversation with active bots
		const starterConversation = buildStarterConversation(starterBots);
		conversations = [starterConversation];
		currentConversationId = starterConversation.id;
		
		// Pre-load the starter question in the input
		currentInputMessage = STARTER_MESSAGE;
		
		// Save conversations
		saveConversations();
	}

	function toggleActiveBotsExpanded() {
		if (currentConversation) {
			currentConversation.activeBotsExpanded = !currentConversation.activeBotsExpanded;
			conversations = conversations;
			saveConversations();
		}
	}

	function toggleResponseModifier() {
		if (currentConversation) {
			const current = currentConversation.responseModifier || 'none';
			const nextState: ResponseModifier = current === 'none' ? 'chat' : current === 'chat' ? 'deep' : 'none';
			currentConversation.responseModifier = nextState;
			conversations = conversations;
			saveConversations();
		}
	}

	function reorderConversations(fromIndex: number, toIndex: number) {
		const [removed] = conversations.splice(fromIndex, 1);
		conversations.splice(toIndex, 0, removed);
		conversations = conversations;
		saveConversations();
	}

	function updateConversationName(conversationId: string, newName: string) {
		// Validate uniqueness
		if (conversations.some(c => c.id !== conversationId && c.name === newName)) {
			duplicateNameErrorOpen = true;
			return;
		}

		const conv = conversations.find(c => c.id === conversationId);
		if (conv && newName.trim()) {
			conv.name = newName.trim();
			conversations = conversations;
			renamingConvId = null;
			renameInputValue = '';
			saveConversations();
		}
	}

	function updateConversationDescription(conversationId: string, newDescription: string) {
		const conv = conversations.find(c => c.id === conversationId);
		if (conv) {
			conv.description = newDescription;
			conversations = conversations;
			editingDescriptionId = null;
			saveConversations();
		}
	}

	// Auto-focus directive for rename input
	function focusInput(node: HTMLInputElement) {
		node.focus();
		node.select();
		return {};
	}

	function startRenaming(conversationId: string, currentName: string) {
		renamingConvId = conversationId;
		renameInputValue = currentName;
	}

	function startEditingDescription(conversationId: string) {
		editingDescriptionId = conversationId;
	}

	function handleConversationDragStart(e: DragEvent, conversationId: string) {
		draggedConvId = conversationId;
		if (e.dataTransfer) {
			e.dataTransfer.effectAllowed = 'move';
		}
	}

	function handleConversationDragOver(e: DragEvent, index: number) {
		e.preventDefault();
		if (e.dataTransfer) {
			e.dataTransfer.dropEffect = 'move';
		}
		
		// Only show indicator if actually dragging
		if (draggedConvId) {
			const target = e.currentTarget as HTMLElement;
			const rect = target.getBoundingClientRect();
			const midpoint = rect.left + rect.width / 2;
			
			// Determine if hovering over left or right half
			dragOverSide = e.clientX < midpoint ? 'left' : 'right';
			// Always use current index, side determines which border to show
			dropIndicatorIndex = index;
		}
	}

	function handleConversationDrop(e: DragEvent, dropIndex: number) {
		e.preventDefault();
		if (!draggedConvId) return;

		const dragIndex = conversations.findIndex(c => c.id === draggedConvId);
		// If dropping on right side, insert after the hovered tab (dropIndex + 1)
		const finalDropIndex = dragOverSide === 'right' ? dropIndex + 1 : dropIndex;
		
		if (dragIndex !== finalDropIndex && dragIndex !== -1) {
			reorderConversations(dragIndex, finalDropIndex);
		}
		draggedConvId = null;
		dropIndicatorIndex = null;
		dragOverSide = null;
	}

	function handleConversationClick(conversationId: string) {
		// Prevent switching while responses are streaming in
		if (streamingCount > 0) {
			return; // Can't switch conversations while streaming
		}
		
		// Only switch if we didn't actually drag
		if (currentConversationId !== conversationId) {
			// Save current conversation's messages before switching
			saveMessages();
			
			// Switch to new conversation
			currentConversationId = conversationId;
			currentConversation = conversations.find(c => c.id === conversationId) || null;
			
			// Load messages for this conversation (or empty if new)
			messages = conversationMessages[conversationId] || [];
			
			saveConversations();
		}
	}

	// Mobile panel handlers
	function openMobilePanel(panel: 'library' | 'chats' | 'newbot' | 'attachments' | 'settings') {
		if (panel === 'settings') {
			settingsOpen = true;
		} else {
			mobilePanel = panel;
		}
	}

	function closeMobilePanel() {
		mobilePanel = 'none';
	}

	// Intro modal handlers
	function handleIntroOk() {
		// Close modal but don't set dismissal flag - will show again next login
		introOpen = false;
	}

	function handleIntroDismiss() {
		// Close modal and set dismissal flag - won't show again unless localStorage cleared
		introOpen = false;
		setUserItem('introModalDismissed', 'true');
	}

	function checkShowIntroModal() {
		// Show intro modal if user hasn't permanently dismissed it
		const dismissed = getUserItem('introModalDismissed');
		if (dismissed !== 'true') {
			introOpen = true;
		}
	}

	function handleMobileConversationSelect(id: string) {
		handleConversationClick(id);
		closeMobilePanel();
	}

	function handleMobileConversationCreate() {
		createNewConversation();
		closeMobilePanel();
	}

	function handleMobileConversationDelete(id: string) {
		confirmCloseChat(id);
	}

	function handleMobileConversationRename(detail: { id: string; name: string }) {
		updateConversationName(detail.id, detail.name);
	}

	function retryFailedMessage(errorMsg: Message) {
		if (!errorMsg.lastInputs) return;
		
		// Restore the message and attachments
		const messageToSend = errorMsg.lastInputs.message;
		globalAttachments = errorMsg.lastInputs.attachments;
		
		// Remove the error message from the list
		messages = messages.filter((m) => m.id !== errorMsg.id);
		
		// Resend the message with the same inputs
		sendMessage(messageToSend);
	}

	onMount(() => {
		// Mobile detection
		const checkMobile = () => {
			isMobile = window.innerWidth < 768; // md breakpoint
			// Close mobile panel if switching to desktop
			if (!isMobile && mobilePanel !== 'none') {
				mobilePanel = 'none';
			}
		};
		checkMobile();
		window.addEventListener('resize', checkMobile);

		// Migrate existing data to user-namespaced storage (one-time, per user)
		if ($isAuthenticated) {
			const migration = migrateUserData();
			if (migration.migrated) {
				console.log('[UserStorage] Migrated data for current user:', migration.keys);
			}
		}

		// Load conversations first, then messages
		loadConversations();
		loadMessages();

		// Fetch subscription status if authenticated
		if ($isAuthenticated) {
			subscription.fetchStatus();
			quota.fetchQuota();
			// Load provider configuration
			loadProviderConfig();
		}

		// Load theme from localStorage (global, not user-specific)
		const savedTheme = getGlobalItem('theme') as 'light' | 'dark' | null;
		if (savedTheme) {
			theme = savedTheme;
			applyTheme(savedTheme);
		} else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
			theme = 'dark';
			applyTheme('dark');
		}

		// Load user-specific settings
		const savedGlobalMaxTokens = getUserItem('globalMaxTokens');
		if (savedGlobalMaxTokens !== null) {
			globalMaxTokens = JSON.parse(savedGlobalMaxTokens);
		}

		// Load bots from user-namespaced localStorage
		// Bots are stored persistently and never auto-deleted
		// Users have full control to delete them via the "Clear All" button or individual delete buttons
		const stored = getUserItem('savedBots');
		if (stored) {
			try {
				bots = JSON.parse(stored).map((b: any) => ({
					...b,
					systemInstructionFile: undefined, // Files can't be serialized
					maxTokens: b.maxTokens, // Preserve maxTokens
					category: b.category // Preserve category
				}));
			} catch (e) {
				console.error('Failed to load bots:', e);
			}
		}

		// Show intro modal for users who haven't dismissed it
		if ($isAuthenticated) {
			checkShowIntroModal();
		}

		// Listen for close event from SummaryResultModal
		document.addEventListener('closeSummaryModal', closeSummaryModal);

		// Listen for Escape key to close modals and 's' to toggle sidebar
		const handleEscape = (e: KeyboardEvent) => {
			// Check if user is typing in an input/textarea
			const isTyping = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement;

			if (e.key === 'Escape') {
				if (settingsOpen) {
					settingsOpen = false;
				} else if (removeAllConfirmOpen) {
					cancelRemoveAllBots();
				} else if (clearConvConfirmOpen) {
					cancelClearConversation();
				} else if (duplicateNameErrorOpen) {
					duplicateNameErrorOpen = false;
				} else if (exportModalOpen) {
					exportModalOpen = false;
				}
			} else if (e.key === 'Enter') {
				if (removeAllConfirmOpen) {
					e.preventDefault();
					confirmRemoveAllBots();
				} else if (clearConvConfirmOpen) {
					e.preventDefault();
					clearConversation();
				}
			} else if (e.key === 's' && !isTyping && !e.ctrlKey && !e.metaKey && !e.altKey && !e.shiftKey) {
				// Toggle sidebar with 's' hotkey (only when not typing and no modifier keys)
				e.preventDefault();
				sidebarOpen = !sidebarOpen;
			}
		};
		document.addEventListener('keydown', handleEscape);

		return () => {
			document.removeEventListener('closeSummaryModal', closeSummaryModal);
			document.removeEventListener('keydown', handleEscape);
			window.removeEventListener('resize', checkMobile);
		};
	});

	async function saveBotConfig(bot: Bot) {
		// Read system instruction file content if present (file takes precedence over text)
		let systemInstructionText = bot.systemInstructionText || '';
		if (bot.systemInstructionFile) {
			try {
				systemInstructionText = await readFileContent(bot.systemInstructionFile);
			} catch (error) {
				console.error('Failed to read system instruction file:', error);
				// Fall back to text if file read fails
			}
		}
		
		// Create a named copy for the library
		const savedBot: Bot = {
			...bot,
			id: crypto.randomUUID(),
			name: bot.name || `${bot.provider} - ${bot.model}`,
			systemInstructionText,
			systemInstructionFile: undefined,
			maxTokens: bot.maxTokens,
			category: bot.category
		};
		bots = [...bots, savedBot];
		// Persist to local storage (without File objects)
		const serializable = bots.map((b) => ({
			id: b.id,
			provider: b.provider,
			model: b.model,
			name: b.name,
			systemInstructionText: b.systemInstructionText,
			maxTokens: b.maxTokens,
			category: b.category
		}));
		setUserItem('savedBots', JSON.stringify(serializable));
		return savedBot;
	}

	async function addBotToConversation(bot: Bot) {
		// Check tier limits for bots per conversation (check currentConversation directly for real-time count)
		const currentCount = currentConversation?.activeBots?.length ?? 0;
		if (currentCount >= $tierLimits.maxBotsPerConversation) {
			const tierText = $isPaidUser ? 'Subscriber' : 'Free';
			showAlert('Bot Limit Reached', `${tierText} tier limit: ${$tierLimits.maxBotsPerConversation} bots per chat maximum.`, 'warning');
			return;
		}
		
		const newBot: Bot = {
			...bot,
			id: crypto.randomUUID()
		};
		
		// Read file content if present (file takes precedence over text)
		if (newBot.systemInstructionFile) {
			try {
				newBot.systemInstructionText = await readFileContent(newBot.systemInstructionFile);
				newBot.systemInstructionFile = undefined; // Clear the File object
			} catch (error) {
				console.error('Failed to read system instruction file:', error);
				// Keep existing text if file read fails
			}
		}
		
		if (currentConversation) {
			currentConversation.activeBots = [...currentConversation.activeBots, newBot];
			conversations = conversations;
			saveConversations();
		}
	}

	function removeBotFromConversation(botId: string) {
		if (currentConversation) {
			currentConversation.activeBots = currentConversation.activeBots.filter((b) => b.id !== botId);
			conversations = conversations;
			saveConversations();
		}
	}

	function removeAllBotsFromConversation() {
		removeAllConfirmOpen = true;
	}

	function confirmRemoveAllBots() {
		if (currentConversation) {
			currentConversation.activeBots = [];
			conversations = conversations;
			saveConversations();
		}
		removeAllConfirmOpen = false;
	}

	function cancelRemoveAllBots() {
		removeAllConfirmOpen = false;
	}

	function removeBotFromAll(botId: string) {
		// Remove from current conversation's active bots
		if (currentConversation) {
			currentConversation.activeBots = currentConversation.activeBots.filter((b) => b.id !== botId);
			conversations = conversations;
			saveConversations();
		}
	}

	function openEditActiveBot(bot: Bot) {
		editingActiveBot = bot;
		editBotDialogOpen = true;
	}

	function handleSaveActiveBot(event: CustomEvent<Bot>) {
		const updatedBot = event.detail;
		if (currentConversation && updatedBot) {
			const index = currentConversation.activeBots.findIndex(b => b.id === updatedBot.id);
			if (index >= 0) {
				currentConversation.activeBots[index] = updatedBot;
				conversations = conversations;
				saveConversations();
			}
		}
		editBotDialogOpen = false;
		editingActiveBot = null;
	}

	function handleCancelEditActiveBot() {
		editBotDialogOpen = false;
		editingActiveBot = null;
	}

	function getSystemInstructionText(bot: Bot): string {
		return bot.systemInstructionText || '';
	}

	function buildConversationHistory(excludeLatest: boolean = false): string {
		if (messages.length === 0) return '';

		let messagesToInclude = messages;
		if (excludeLatest && messages.length > 0) {
			messagesToInclude = messages.slice(0, -1);
		}

		let history = '';
		for (const msg of messagesToInclude) {
			if (msg.role === 'user') {
				history += `**You:** ${msg.content}\n\n`;
			} else {
				const botLabel = msg.model ? `**${msg.provider} (${msg.model})**` : '**Assistant**';
				history += `${botLabel}: ${msg.content}\n\n`;
			}
		}
		return history;
	}

	async function sendMessage(userMessage: string) {
		if (!userMessage.trim() || activeBots.length === 0) return;
		if (hasOversizedAttachments) {
			messages = [
				...messages,
				{
					id: crypto.randomUUID(),
					role: 'assistant',
					content: '❌ **Cannot send message** — One or more attachments exceed the 50MB size limit. Please remove oversized files from the Attachments section before sending.',
					timestamp: Date.now(),
					isError: true
				}
			];
			return;
		}
		
		// Check if user has authentication (either API key or OAuth JWT)
		const headers = authHeaders();
		const hasAuth = API_KEY || headers.Authorization;
		if (!hasAuth) {
			// Check if they were previously authenticated (session expired)
			const wasAuthenticated = $isAuthenticated;
			messages = [
				...messages,
				{
					id: crypto.randomUUID(),
					role: 'assistant',
					content: wasAuthenticated 
						? '⚠️ **Session expired** — Please sign in again to continue chatting.'
						: 'Please sign in to send messages.',
					timestamp: Date.now()
				}
			];
			// Open sign in modal if session expired
			if (wasAuthenticated) {
				signInOpen = true;
			}
			return;
		}

		// Check for bots that exceed context window limit
		const botsExceedingLimit: Bot[] = [];
		const botsWithinLimit: Bot[] = [];
		
		for (const bot of activeBots) {
			const inputTokens = estimateTokensForBot(bot, userMessage);
			const contextWindow = getContextWindow(bot.provider, bot.model);
			
			if (inputTokens >= contextWindow) {
				botsExceedingLimit.push(bot);
			} else {
				botsWithinLimit.push(bot);
			}
		}

		isLoading = true;
		currentRunAbortController = new AbortController();
		
		// Clear any leftover streaming state from previous runs
		currentStreamingMessageIds.clear();
		streamingCount = 0;

		// Add user message
		const userMsg: Message = {
			id: crypto.randomUUID(),
			role: 'user',
			content: userMessage,
			timestamp: Date.now()
		};
		messages = [...messages, userMsg];

		// Add error messages for bots that exceed context window
		for (const bot of botsExceedingLimit) {
			const inputTokens = estimateTokensForBot(bot, userMessage);
			const contextWindow = getContextWindow(bot.provider, bot.model);
			const botLabel = bot.name || `${bot.provider} (${bot.model})`;
			
			const errorMsg: Message = {
				id: crypto.randomUUID(),
				role: 'assistant',
				content: `❌ **${botLabel}** - Context window exceeded\n\nThis message (~${inputTokens.toLocaleString()} tokens) exceeds the model's context window limit of ${contextWindow.toLocaleString()} tokens.\n\nTry: (1) Clearing conversation history, (2) Removing attachments, or (3) Using a model with larger context window.`,
				timestamp: Date.now(),
				botId: bot.id,
				provider: bot.provider,
				model: bot.model,
				isError: true
			};
			messages = [...messages, errorMsg];
		}

		// If no bots can handle the message, we're done
		if (botsWithinLimit.length === 0) {
			isLoading = false;
			currentRunAbortController = null;
			return;
		}

		// Get encryption key for decrypting API keys
		const encryptionKey = await getEncryptionKey();
		console.log('[BYOK] Encryption key available:', !!encryptionKey);
		
		// Create configs only for bots within limit, including decrypted provider keys
		let platformKeyCount = 0; // Track bots using platform keys for optimistic quota update
		const configs = await Promise.all(botsWithinLimit.map(async (bot) => {
			let providerKey: string | null = null;
			
			// Try to get the decrypted provider key from localStorage
			if (encryptionKey) {
				providerKey = await getProviderKey(bot.provider, encryptionKey);
				console.log(`[BYOK] Provider key for ${bot.provider}:`, providerKey ? 'found' : 'not found');
			}
			
			// Count bots that will use platform keys (no BYOK)
			if (!providerKey) {
				platformKeyCount++;
			}
			
			return {
				id: bot.id,
				provider: bot.provider,
				model: bot.model,
				system: getSystemInstructionText(bot),
				max_tokens: bot.maxTokens || globalMaxTokens,
				provider_key: providerKey // Will be null if not configured (backend falls back to env)
			};
		}));
		
		// Optimistic quota update for immediate UI feedback
		// This increments the displayed count before server confirms
		// Server response (run_done) will reconcile with actual values
		if (platformKeyCount > 0 && $isAuthenticated) {
			quota.incrementUsed(platformKeyCount);
		}

		try {
			// Build conversation history (all previous messages excluding the one we just added)
			const conversationHistory = buildConversationHistory(true);
			
			// Determine response modifier suffix
			const modifier = currentConversation?.responseModifier || 'none';
			const modifierSuffix = modifier === 'chat' ? CHAT_MODIFIER : modifier === 'deep' ? DEEP_MODIFIER : '';
			
			// Combine history with new message and modifier
			// History is only included if there are previous messages
			const baseMessage = conversationHistory 
				? `## Conversation History\n\n${conversationHistory}\n---\n\n## New Message\n\n${userMessage}`
				: userMessage;
			const messageToSend = baseMessage + modifierSuffix;

			// Build FormData for multipart request
			const formData = new FormData();
			formData.append('message', messageToSend);
			formData.append('configs', JSON.stringify(configs));
			formData.append('max_parallel', '10');
			
			// Append all files
			for (const file of globalAttachments) {
				formData.append('attachments', file);
			}

			const response = await fetch(`${API_BASE}/runs`, {
				method: 'POST',
				headers: authHeaders(),
				body: formData
			});

			if (!response.ok) {
				// Check for authentication failure (401 = token invalid/expired)
				if (response.status === 401) {
					// Clear stale auth and prompt re-login
					logout();
					messages = [
						...messages,
						{
							id: crypto.randomUUID(),
							role: 'assistant',
							content: '⚠️ **Session expired** — Your authentication token is no longer valid. Please sign in again to continue.',
							timestamp: Date.now(),
							isError: true
						}
					];
					signInOpen = true;
					isLoading = false;
					currentRunAbortController = null;
					return;
				}
				// Parse error detail from backend
				let errorDetail = 'Failed to create run';
				try {
					const errorJson = await response.json();
					errorDetail = errorJson.detail || errorDetail;
				} catch {
					// If not JSON, use status text
					errorDetail = response.statusText || errorDetail;
				}
				throw new Error(errorDetail);
			}
			const { run_id } = await response.json();

			// Stream events
			await streamEvents(run_id);
		} catch (error) {
			console.error('Error:', error);
			// Don't show error message if it was an abort (user cancelled)
			if (error instanceof Error && error.name !== 'AbortError') {
				messages = [
					...messages,
					{
						id: crypto.randomUUID(),
						role: 'assistant',
						content: `Error: ${error.message}`,
						timestamp: Date.now()
					}
				];
			}
		} finally {
			isLoading = false;
			currentRunAbortController = null;
			// Refresh quota after message completion (quota was incremented on backend)
			if ($isAuthenticated) {
				quota.fetchQuota();
			}
		}
	}

	function cancelMessage() {
		if (currentRunAbortController) {
			currentRunAbortController.abort();
		}
		// Clear streaming state so next message creates fresh responses
		currentStreamingMessageIds.clear();
		streamingCount = 0;
	}

	async function streamEvents(runId: string) {
		try {
			const response = await fetch(`${API_BASE}/runs/${runId}/events`, {
				headers: authHeaders(),
				cache: 'no-store',
				signal: currentRunAbortController?.signal
			});
			if (!response.body) throw new Error('No response body');

			const reader = response.body.getReader();
			const decoder = new TextDecoder();
			let buffer = '';

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() || '';

				for (let i = 0; i < lines.length; i++) {
					const line = lines[i];
					if (line.startsWith('event: ')) {
						const eventType = line.substring(7);
						const nextIdx = i + 1;
						const dataLine = lines[nextIdx];

						if (dataLine && dataLine.startsWith('data: ')) {
							const data = JSON.parse(dataLine.substring(6));

							if (eventType === 'panel_token') {
								// Track streaming messages by config_id to avoid appending to previous responses
								let messageId = currentStreamingMessageIds.get(data.config_id);
								if (!messageId) {
									// First token for this response - create the message
									const bot = activeBots.find((b) => b.id === data.config_id);
									const newMsg: Message = {
										id: crypto.randomUUID(),
										role: 'assistant',
										content: data.token,
										timestamp: Date.now(),
										botId: data.config_id,
										provider: bot?.provider,
										model: bot?.model
									};
									messages = [...messages, newMsg];
									currentStreamingMessageIds.set(data.config_id, newMsg.id);
									streamingCount = currentStreamingMessageIds.size; // Keep reactive counter in sync
								} else {
									// Append to the current streaming message
									const msg = messages.find((m) => m.id === messageId);
									if (msg) {
										msg.content += data.token;
										messages = [...messages];
									}
								}
							} else if (eventType === 'panel_final') {
								// Update or create final message
								const messageId = currentStreamingMessageIds.get(data.config_id);
								// Detect truncation from finish_reason
								const TRUNCATION_REASONS = new Set(['length', 'max_tokens', 'MAX_TOKENS']);
								const isTruncated = data.finish_reason && TRUNCATION_REASONS.has(data.finish_reason);
								
								if (messageId) {
									// Update the streamed message with final content
									const msg = messages.find((m) => m.id === messageId);
									if (msg) {
										msg.content = data.final;
										msg.isTruncated = isTruncated;
										msg.finishReason = data.finish_reason;
										messages = [...messages];
									}
									currentStreamingMessageIds.delete(data.config_id);
									streamingCount = currentStreamingMessageIds.size;
								} else {
									// Fallback: create message if streaming didn't occur
									const bot = activeBots.find((b) => b.id === data.config_id);
									const msg: Message = {
										id: crypto.randomUUID(),
										role: 'assistant',
										content: data.final,
										timestamp: Date.now(),
										botId: data.config_id,
										provider: bot?.provider,
										model: bot?.model,
										isTruncated,
										finishReason: data.finish_reason
									};
									messages = [...messages, msg];
								}
							} else if (eventType === 'panel_error') {
								// Handle provider-specific errors (including missing API keys)
								const messageId = currentStreamingMessageIds.get(data.config_id);
								const bot = activeBots.find((b) => b.id === data.config_id);
								const botLabel = bot ? `${bot.provider} (${bot.model})` : 'Unknown bot';
								
								// Remove any partial/blank streaming message for this bot
								if (messageId) {
									messages = messages.filter((m) => m.id !== messageId);
									currentStreamingMessageIds.delete(data.config_id);
									streamingCount = currentStreamingMessageIds.size;
								}
								
								// Create error message to display to user
								const errorMessage = `❌ **${botLabel}** failed: ${data.error}`;
								
								// Get the last user message for retry functionality
								const lastUserMessage = messages.filter(m => m.role === 'user').pop();
								
								const errorMsg: Message = {
									id: crypto.randomUUID(),
									role: 'assistant',
									content: errorMessage,
									timestamp: Date.now(),
									botId: data.config_id,
									provider: bot?.provider,
									model: bot?.model,
									isError: true,
									lastInputs: {
										message: lastUserMessage?.content || '',
										attachments: globalAttachments
									}
								};
								messages = [...messages, errorMsg];
							} else if (eventType === 'run_error') {
								// Handle general run-level errors
								const errorMsg: Message = {
									id: crypto.randomUUID(),
									role: 'assistant',
									content: `❌ **Run failed:** ${data.error}`,
									timestamp: Date.now()
								};
								messages = [...messages, errorMsg];
								// Clear all streaming state
								currentStreamingMessageIds.clear();
								streamingCount = 0;
							} else if (eventType === 'run_done') {
								// Run completed - update quota immediately if included
								if (data.quota) {
									quota.setQuota({
										used: data.quota.used ?? 0,
										limit: data.quota.limit ?? 100,
										remaining: data.quota.remaining ?? 100,
										periodEndsAt: data.quota.period_ends_at ?? null,
										isPaid: data.quota.is_paid ?? false,
									});
								}
							}
						}
					}
				}
			}
		} catch (error) {
			console.error('Stream error:', error);
		}
	}

	function exportConversation() {
		exportModalOpen = true;
	}

	function generateExportMarkdown(): string {
		let markdown = `# botchat | many minds, no memory

**botchat Chat Export**

`;
		markdown += `**Exported:** ${new Date().toLocaleString()}\n\n`;

		if (activeBots.length > 0) {
			markdown += `**Bots:** ${activeBots.map((b) => `${b.name} (${b.provider} - ${b.model})`).join(', ')}\n\n`;
		}

		if (globalAttachments.length > 0) {
			markdown += `## Attachments\n\n`;
			globalAttachments.forEach((f) => {
				markdown += `- ${f.name}\n`;
			});
			markdown += `\n`;
		}

		markdown += `## Chat\n\n`;

		for (const msg of messages) {
			if (msg.role === 'user') {
				markdown += `### 👤 User\n\n${msg.content}\n\n`;
			} else {
				// Look up bot name from activeBots using botId
				const bot = activeBots.find((b) => b.id === msg.botId);
				const botName = bot?.name || 'Assistant';
				const botLabel = msg.model ? `${botName} (${msg.provider} / ${msg.model})` : botName;
				const heading = `### 🤖 ${botLabel}`;

				markdown += `${heading}\n\n${msg.content}\n\n`;
			}
		}
		return markdown;
	}

	function exportPrint() {
		exportModalOpen = false;
		const markdown = generateExportMarkdown();
		
		// Create a print-friendly HTML version
		const printWindow = window.open('', '_blank');
		if (!printWindow) return;
		
		// Convert markdown to simple HTML for printing
		const htmlContent = markdown
			.replace(/^# botchat \| many minds, no memory$/gm, '<h1>botchat | many minds, no memory</h1>')
			.replace(/^# (.+)$/gm, '<h2>$1</h2>')
			.replace(/^## (.+)$/gm, '<h2>$1</h2>')
			.replace(/^### (.+)$/gm, '<h3>$1</h3>')
			.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
			.replace(/^- (.+)$/gm, '<li>$1</li>')
			.replace(/\n\n/g, '</p><p>')
			.replace(/\n/g, '<br>');
		
		printWindow.document.write(`
			<!DOCTYPE html>
			<html>
			<head>
				<title>Chat Export</title>
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
			<body><p>${htmlContent}</p></body>
			</html>
		`);
		printWindow.document.close();
		printWindow.print();
	}

	function exportSave() {
		exportModalOpen = false;
		const markdown = generateExportMarkdown();
		
		const blob = new Blob([markdown], { type: 'text/plain' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `botchat-chat-${Date.now()}.txt`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}

	function clearConversation() {
		messages = [];
		// Clear from sessionStorage as well
		if (currentConversationId) {
			clearConversationMessages(currentConversationId);
		}
		currentStreamingMessageIds.clear();
		streamingCount = 0;
		clearConvConfirmOpen = false;
	}

	function exportConfig() {
		// Gather all configuration data
		const storedCategories = getUserItem('botCategories');
		const config = {
			version: '1.0',
			exportedAt: new Date().toISOString(),
			bots: bots,
			conversations: conversations,
			categories: storedCategories ? JSON.parse(storedCategories) : [],
			settings: {
				// Add any app-level settings here if needed
				theme: getGlobalItem('theme') || 'auto'
			}
		};

		const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `botchat-config-${Date.now()}.json`;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}

	function importConfig() {
		const input = document.createElement('input');
		input.type = 'file';
		input.accept = '.json';
		input.onchange = async (e: Event) => {
			const file = (e.target as HTMLInputElement).files?.[0];
			if (!file) return;

			try {
				const text = await file.text();
				const config = JSON.parse(text);

				// Validate config structure
				if (!config.bots || !Array.isArray(config.bots)) {
					throw new Error('Invalid config: missing bots array');
				}
				if (!config.conversations || !Array.isArray(config.conversations)) {
					throw new Error('Invalid config: missing conversations array');
				}

				// Store config and show confirmation modal
				pendingImportConfig = config;
				importConfirmOpen = true;
			} catch (error) {
				importResultSuccess = false;
				importResultMessage = error instanceof Error ? error.message : 'Unknown error';
				importResultOpen = true;
			}
		};
		input.click();
	}

	async function confirmImport() {
		if (!pendingImportConfig) return;
		
		try {
			// Restore categories FIRST (so bots can reference them)
			if (pendingImportConfig.categories && Array.isArray(pendingImportConfig.categories)) {
				setUserItem('botCategories', JSON.stringify(pendingImportConfig.categories));
			}

			// Restore bots
			bots = pendingImportConfig.bots;
			setUserItem('savedBots', JSON.stringify(bots));

			// Restore conversations
			conversations = pendingImportConfig.conversations;
			setUserItem('conversations', JSON.stringify(conversations));

			// Restore theme (global setting)
			if (pendingImportConfig.settings?.theme) {
				const importedTheme = pendingImportConfig.settings.theme as 'light' | 'dark';
				setGlobalItem('theme', importedTheme);
				theme = importedTheme;
				applyTheme(importedTheme);
			}

			// Dispatch event to notify BotLibrary that categories have changed
			window.dispatchEvent(new CustomEvent('categoriesUpdated'));
			
			// Reload provider configuration to update the UI
			await loadProviderConfig();

			importConfirmOpen = false;
			importResultSuccess = true;
			importResultMessage = 'Configuration imported successfully!';
			importResultOpen = true;
			pendingImportConfig = null;
		} catch (error) {
			importConfirmOpen = false;
			importResultSuccess = false;
			importResultMessage = error instanceof Error ? error.message : 'Unknown error';
			importResultOpen = true;
			pendingImportConfig = null;
		}
	}

	function cancelImport() {
		importConfirmOpen = false;
		pendingImportConfig = null;
	}

	function closeImportResult() {
		importResultOpen = false;
		// Auto-refresh page after successful import to ensure bots work properly
		if (importResultSuccess) {
			window.location.reload();
		}
	}

	function showClearConvConfirmation() {
		clearConvConfirmOpen = true;
	}

	function cancelClearConversation() {
		clearConvConfirmOpen = false;
	}

	async function summarizeConversation(selectedBotId: string) {
		const selectedBot = bots.find((b) => b.id === selectedBotId);
		if (!selectedBot || messages.length === 0) return;

		// Get encryption key for decrypting API keys
		const encryptionKey = await getEncryptionKey();
		let providerKey: string | null = null;
		
		if (encryptionKey) {
			providerKey = await getProviderKey(selectedBot.provider, encryptionKey);
		}
		
		// Note: If no BYOK key, backend will use platform keys as fallback

		isSummarizing = true;
		selectedSummaryBot = selectedBot;
		// Keep summarizeOpen = true so modal stays visible during loading

		// Build full conversation text
		const conversationText = messages
			.map((msg) => {
				if (msg.role === 'user') {
					return `**You:** ${msg.content}`;
				} else {
					// Look up bot name from activeBots using botId
					const bot = activeBots.find((b) => b.id === msg.botId);
					const botName = bot?.name || 'Assistant';
					const botLabel = msg.model ? `**${botName} (${msg.provider} / ${msg.model})**` : `**${botName}**`;
					return `${botLabel}: ${msg.content}`;
				}
			})
			.join('\n\n');

		// Create summarize prompt
		const summarizePrompt = `Please summarize this entire conversation and distill the key points down to no more than one printed page.\n\n${conversationText}`;

		// Create a bot config for the selected bot (including provider_key for BYOK)
		const config = {
			id: crypto.randomUUID(),
			provider: selectedBot.provider,
			model: selectedBot.model,
			system: selectedBot.systemInstructionText || '',
			max_tokens: selectedBot.maxTokens || globalMaxTokens,
			provider_key: providerKey  // BYOK key (null if not configured, backend falls back to env)
		};

		try {
			// Build FormData for multipart request
			const formData = new FormData();
			formData.append('message', summarizePrompt);
			formData.append('configs', JSON.stringify([config]));
			formData.append('max_parallel', '1');

			// Append all global attachments if needed
			for (const file of globalAttachments) {
				formData.append('attachments', file);
			}

			console.log('Creating summarization run with config:', config);
			const response = await fetch(`${API_BASE}/runs`, {
				method: 'POST',
				headers: authHeaders(),
				body: formData
			});

			if (!response.ok) {
				let errorDetail = 'Unknown error';
				try {
					const errorJson = await response.json();
					errorDetail = errorJson.detail || 'Unknown error';
				} catch {
					errorDetail = await response.text();
				}
				console.error('Failed to create run:', response.status, errorDetail);
				throw new Error(errorDetail);
			}
			
			const responseData = await response.json();
			console.log('Run created:', responseData);
			const { run_id } = responseData;

			if (!run_id) {
				throw new Error('No run_id in response');
			}

			let summaryText = '';

			// Stream results using fetch (like the regular chat does) to support custom headers
			console.log('Streaming from:', `${API_BASE}/runs/${run_id}/events`);
			try {
				const response = await fetch(`${API_BASE}/runs/${run_id}/events`, {
					headers: authHeaders(),
					cache: 'no-store'
				});
				if (!response.body) throw new Error('No response body');

				const reader = response.body.getReader();
				const decoder = new TextDecoder();
				let buffer = '';

				while (true) {
					const { done, value } = await reader.read();
					if (done) break;

					buffer += decoder.decode(value, { stream: true });
					const lines = buffer.split('\n');
					buffer = lines.pop() || '';

					for (const line of lines) {
						if (line.startsWith('event: ')) {
							const eventType = line.substring(7);
							const nextIdx = lines.indexOf(line) + 1;
							const dataLine = lines[nextIdx];

							if (dataLine && dataLine.startsWith('data: ')) {
								const data = JSON.parse(dataLine.substring(6));
								console.log(`Received ${eventType} event:`, data);

								if (eventType === 'panel_final') {
									summaryText = data.final;
									console.log('Summary received:', summaryText);
									break;
								}
							}
						}
					}
				}

				// Show result modal
				if (summaryText) {
					summaryContent = summaryText;
				} else {
					summaryContent = '❌ No summary was generated. The bot may not have responded.';
				}
				summaryResultOpen = true;
				isSummarizing = false;
				// Refresh quota after summarization
				if ($isAuthenticated) {
					quota.fetchQuota();
				}
			} catch (streamError) {
				console.error('Stream error:', streamError);
				summaryContent = `❌ Failed to stream summary: ${streamError instanceof Error ? streamError.message : 'Unknown error'}`;
				summaryResultOpen = true;
				isSummarizing = false;
				// Refresh quota even on error (message may have been counted)
				if ($isAuthenticated) {
					quota.fetchQuota();
				}
			}
		} catch (error) {
			console.error('Summarization error:', error);
			summaryContent = `❌ Error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`;
			summaryResultOpen = true;
			isSummarizing = false;
			// Refresh quota even on error
			if ($isAuthenticated) {
				quota.fetchQuota();
			}
		}
	}

	function closeSummaryModal() {
		summaryResultOpen = false;
	}

	// Check if providers are configured (for mobile nav indicator)
	$: hasConfiguredProviders = $configuredProviderIds.length > 0;
</script>

<svelte:head>
	<title>botchat | many minds, no memory</title>
</svelte:head>

{#if $authLoading}
	<!-- Loading state while checking authentication -->
	<div class="h-screen flex flex-col items-center justify-center bg-white dark:bg-gray-900">
		<div class="text-center space-y-4">
			<h1 class="text-4xl font-bold text-blue-600 dark:text-blue-400">botchat</h1>
			<p class="text-gray-500 dark:text-gray-400">Loading...</p>
		</div>
	</div>
{:else if !$isSessionValid}
	<!-- Sign-in gate: User must be authenticated to use the app -->
	<div class="h-screen flex flex-col bg-white dark:bg-gray-900">
		<!-- Header -->
		<div class="bg-gradient-to-r from-blue-600 to-blue-700 dark:from-blue-800 dark:to-blue-900 text-white px-4 py-2 shadow">
			<div class="flex items-center justify-between">
				<div class="flex items-end gap-3">
					<h1 class="text-4xl font-bold leading-none">botchat</h1>
					<p class="text-blue-100 text-xs leading-tight">many minds<br/>no memory</p>
				</div>
				<div class="flex items-center gap-4">
					<a href="mailto:leo@botchat.ca" class="text-sm hover:text-blue-100 transition-colors">Contact</a>
					<button on:click={() => (aboutOpen = true)} class="text-sm hover:text-blue-100 transition-colors">About</button>
				</div>
			</div>
		</div>
		
		<!-- Sign-in prompt - scrollable on mobile -->
		<div class="flex-1 overflow-y-auto">
			<div class="min-h-full flex flex-col items-center justify-center px-6 py-12">
				<div class="max-w-md w-full text-center space-y-10">
					<div class="space-y-4">
						<h2 class="text-3xl font-bold text-gray-900 dark:text-white">Welcome to botchat.</h2>
						<p class="text-gray-600 dark:text-gray-400 leading-relaxed">botchat is a privacy-preserving, multi-bot chat tool that lets you interact with multiple AI models simultaneously.</p>
					</div>
					
					<div class="space-y-6">
						<p class="text-base font-semibold text-gray-700 dark:text-gray-200">
							botchat never retains your chats or attachments.
						</p>
						
						<button
							on:click={() => (signInOpen = true)}
							class="w-full py-4 px-6 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-xl shadow-lg transition-colors text-lg"
						>
							Sign in to get started
						</button>
						
						<p class="text-xs text-gray-400 dark:text-gray-500">
							By signing in, you agree to our <a href="/terms" class="underline hover:text-gray-600 dark:hover:text-gray-300">Terms of Service</a> and <a href="/privacy" class="underline hover:text-gray-600 dark:hover:text-gray-300">Privacy Statement</a>.
						</p>
						
						<p class="text-sm text-gray-500 dark:text-gray-400 leading-relaxed">
							Sign in to try out botchat.
						</p>
					</div>
					
					<div class="pt-10 border-t border-gray-200 dark:border-gray-700">
						<h3 class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-6">What you can do with botchat:</h3>
						<ul class="text-sm text-gray-600 dark:text-gray-400 space-y-4 text-left">
							<li class="flex items-start gap-3">
								<span class="text-blue-500 mt-0.5">✓</span>
								<span>Chat with multiple AI bots in a single conversation</span>
							</li>
							<li class="flex items-start gap-3">
								<span class="text-blue-500 mt-0.5">✓</span>
								<span>Customize personalities and instructions for each bot</span>
							</li>
							<li class="flex items-start gap-3">
								<span class="text-blue-500 mt-0.5">✓</span>
								<span>Privately attach PDFs and images for AI analysis</span>
							</li>
							<li class="flex items-start gap-3">
								<span class="text-blue-500 mt-0.5">✓</span>
								<span>Keep your data 100% private — botchat never stores your data</span>
							</li>
						</ul>
					</div>
				</div>
			</div>
		</div>
	</div>
{:else}
<div class="h-screen flex flex-col bg-white dark:bg-gray-900 transition-colors">
	<!-- Mobile Header (hidden on desktop) -->
	<MobileHeader
		chatName={currentConversation?.name || ''}
		isPaidUser={$isPaidUser}
		isAuthenticated={$isAuthenticated}
		isSessionValid={$isSessionValid}
		messageCount={messages.length}
		responseModifier={currentConversation?.responseModifier || 'none'}
		quotaUsed={$quota.used}
		quotaLimit={$quota.limit}
		isQuotaExhausted={$isQuotaExhausted}
		on:openSignIn={() => (signInOpen = true)}
		on:openSettings={() => (settingsOpen = true)}
		on:openAbout={() => (aboutOpen = true)}
		on:toggleModifier={toggleResponseModifier}
		on:exportChat={exportConversation}
		on:clearChat={showClearConvConfirmation}
		on:summarizeChat={() => (summarizeOpen = true)}
	/>

	<!-- Desktop Header (hidden on mobile) -->
	<div class="hidden md:block bg-gradient-to-r from-blue-600 to-blue-700 dark:from-blue-800 dark:to-blue-900 text-white px-4 py-2 shadow">
		<div class="flex items-center justify-between">
			<div class="flex items-end gap-3">
				<h1 class="text-4xl font-bold leading-none">botchat</h1>
				<p class="text-blue-100 text-xs leading-tight">many minds<br/>no memory</p>
			</div>
			<div class="flex items-center gap-4">
				{#if $isPaidUser}
					<a href="/billing" class="text-sm hover:text-blue-100 transition-colors flex items-center gap-1">
						<span class="px-1.5 py-0.5 bg-teal-300 text-black text-xs rounded font-medium">Subscriber</span>
					</a>
				{:else if $isAuthenticated}
					<a href="/billing" class="text-sm hover:text-blue-100 transition-colors">Subscribe</a>
				{:else}
					<span class="text-sm text-blue-300 opacity-60 cursor-not-allowed" title="Sign in first">Subscribe</span>
				{/if}
				<a href="mailto:leo@botchat.ca" class="text-sm hover:text-blue-100 transition-colors">Contact</a>
				<button on:click={() => (aboutOpen = true)} class="text-sm hover:text-blue-100 transition-colors">About</button>
				<!-- Auth: Login/User Info -->
				<LoginButton on:openSignIn={() => (signInOpen = true)} />
				<button
					on:click={() => (settingsOpen = true)}
					class="p-2 rounded-lg hover:bg-blue-500 dark:hover:bg-blue-700 transition-colors"
					title="Settings"
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
					</svg>
				</button>
			</div>
		</div>
	</div>

	<!-- Main content area -->
	<div class="flex flex-1 overflow-hidden md:gap-4 md:p-4">
		<!-- Desktop Sidebar (~40%) - Collapsible, hidden on mobile -->
		{#if sidebarOpen}
			<div class="hidden md:flex w-2/5 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 shadow-sm flex-col transition-all duration-300 order-1">
				<div class="flex-1 overflow-y-auto space-y-4 pr-2">
				<!-- Bots Library -->
				<BotLibrary 
					savedBots={bots} 
					canAddToConversation={canAddBotToConversation}
					currentBotsInConversation={activeBots.length}
					maxBotsPerConversation={$tierLimits.maxBotsPerConversation}
					on:add={(e: CustomEvent<Bot>) => { addBotToConversation(e.detail); }} 
					on:delete={(e: CustomEvent<string>) => { removeBotFromAll(e.detail); }} 
				/>

				<!-- New Bot Form -->
				<div class="border-b dark:border-gray-700 pb-4">
					<button
						on:click={() => (newBotFormOpen = !newBotFormOpen)}
						class="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
						</svg>
						<span>New Bot</span>
						<span class="text-lg ml-2">{newBotFormOpen ? '▼' : '▶'}</span>
					</button>

					{#if newBotFormOpen}
						<div class="mt-4">
							<NewBotForm
								on:save={async (e: CustomEvent<Bot>) => {
									const saved = await saveBotConfig(e.detail);
									if (saved) {
										await addBotToConversation(saved);
									}
								}}
								on:openSettings={() => (settingsOpen = true)}
							/>
						</div>
					{/if}
				</div>

				<!-- Global Attachment -->
				<div class="border-b dark:border-gray-700 pb-4">
					<button
						on:click={() => (attachmentsOpen = !attachmentsOpen)}
						class="flex items-center gap-2 text-sm font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 transition"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13" />
						</svg>
						<span>Attachments</span>
						<span class="text-lg ml-2">{attachmentsOpen ? '▼' : '▶'}</span>
					</button>

					{#if attachmentsOpen}
						<div class="mt-4">
							<GlobalAttachment bind:files={globalAttachments} bind:hasOversizedFiles={hasOversizedAttachments} />
						</div>
					{/if}
				</div>
			</div>
			
			<!-- Copyright Footer -->
			<div class="pt-2 mt-2 border-t border-gray-200 dark:border-gray-700 text-[10px] text-gray-400 dark:text-gray-500 flex items-center justify-between">
				<div>
					<p>Created by <a href="mailto:leo@botchat.ca" class="hover:text-blue-500">Leo Dias</a></p>
					<p>© 2025</p>
				</div>
				<div class="flex gap-2">
					<a href="/terms" class="hover:text-blue-500">Terms</a>
					<span>·</span>
					<a href="/privacy" class="hover:text-blue-500">Privacy</a>
				</div>
			</div>
		</div>
		{/if}

		<!-- Toggle Button (desktop only) -->
		<button
			on:click={() => (sidebarOpen = !sidebarOpen)}
			class="hidden md:flex items-center justify-center w-12 h-12 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition flex-shrink-0 order-2"
			title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
		>
			{#if sidebarOpen}
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
				</svg>
			{:else}
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19l7-7-7-7" />
				</svg>
			{/if}
		</button>

		<!-- Chat Area (full width on mobile, expands when sidebar is closed on desktop) -->
		<div class="flex flex-col overflow-hidden bg-white md:bg-gray-50 dark:bg-gray-800 md:rounded-lg md:border border-gray-200 dark:border-gray-700 md:shadow-sm transition-all duration-300 flex-1 order-3">
			<!-- Conversation Tabs (desktop only) -->
			<div class="hidden md:flex items-center gap-1 px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
				<!-- Fixed New Tab Button (always first, never scrolls) -->
				<button
					on:click={createNewConversation}
					class={`flex-shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-t-lg transition text-xs font-medium ${
						streamingCount > 0 || !canCreateConversation
							? 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
							: 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800'
					}`}
					title={streamingCount > 0 ? 'Wait for response to complete' : !canCreateConversation ? `Free tier limit: ${$tierLimits.maxConversations} chats` : 'Create new chat'}
					disabled={streamingCount > 0 || !canCreateConversation}
				>
					+ New
				</button>
				<!-- Scrollable Tab Container -->
				<div class="flex items-center gap-1 overflow-x-auto flex-1 min-w-0 scrollbar-thin">
				{#each conversations as conv, index (conv.id)}
					<div
						class={`flex items-center gap-2 px-3 py-1.5 rounded-t-lg transition-all text-xs font-medium whitespace-nowrap relative ${
							draggedConvId === conv.id ? 'opacity-50' : ''
						} ${
							currentConversationId === conv.id
								? 'bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white border-b-2 border-blue-500'
								: streamingCount > 0
									? 'bg-gray-200 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
									: 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 cursor-pointer'
						} ${dropIndicatorIndex === index && dragOverSide === 'left' ? 'border-l-4 border-blue-600 dark:border-blue-400 shadow-[inset_2px_0_0_rgba(37,99,235,0.5)]' : ''} ${dropIndicatorIndex === index && dragOverSide === 'right' ? 'border-r-4 border-blue-600 dark:border-blue-400 shadow-[inset_-2px_0_0_rgba(37,99,235,0.5)]' : ''}`}
						draggable={streamingCount === 0}
						on:dragstart={(e) => handleConversationDragStart(e, conv.id)}
						on:dragover={(e) => handleConversationDragOver(e, index)}
						on:drop={(e) => handleConversationDrop(e, index)}
						on:click={() => handleConversationClick(conv.id)}
						on:keydown={(e) => {
							if (e.key === 'Enter' || e.key === ' ') {
								handleConversationClick(conv.id);
							}
						}}
						on:dragleave={() => {
							if (draggedConvId) {
								dropIndicatorIndex = null;
								dragOverSide = null;
							}
						}}
						role="button"
						tabindex="0"
						title={streamingCount > 0 && currentConversationId !== conv.id ? 'Wait for response to complete' : ''}
					>
						{#if renamingConvId === conv.id}
							<input
								type="text"
								value={renameInputValue}
								on:input={(e) => (renameInputValue = e.currentTarget.value)}
								on:keydown={(e) => {
									if (e.key === 'Enter') {
										updateConversationName(conv.id, renameInputValue);
									} else if (e.key === 'Escape') {
										renamingConvId = null;
										renameInputValue = '';
									}
								}}
								on:blur={() => {
									renamingConvId = null;
									renameInputValue = '';
								}}
								use:focusInput
								class="px-2 py-0.5 text-xs bg-white dark:bg-gray-800 border border-blue-500 rounded text-gray-900 dark:text-white focus:outline-none flex-1 min-w-0"
							/>
						{:else}
							<span
								class="max-w-[120px] truncate cursor-pointer hover:underline"
								on:dblclick={() => startRenaming(conv.id, conv.name)}
								role="button"
								tabindex="0"
							>
								{conv.name}
							</span>
						{/if}
						<button
							on:click|stopPropagation={() => confirmCloseChat(conv.id)}
							class="ml-1 text-gray-500 hover:text-red-600 dark:hover:text-red-400 text-sm leading-none"
							title="Delete chat"
						>
							×
						</button>
					</div>
				{/each}
				</div>
			</div>

			<!-- Chat Header with Description and Action Buttons (desktop only) -->
			{#if currentConversation}
				<div class="hidden md:flex items-center gap-3 px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
					<!-- Description (left side, expandable) -->
					<div class="flex-1 min-w-0">
						{#if editingDescriptionId === currentConversation.id}
							<input
								type="text"
								value={currentConversation.description}
								on:input={(e) => (currentConversation.description = e.currentTarget.value)}
								on:keydown={(e) => {
									if (e.key === 'Enter') {
										updateConversationDescription(currentConversation.id, currentConversation.description);
										editingDescriptionId = null;
									} else if (e.key === 'Escape') {
										editingDescriptionId = null;
										conversations = conversations;
									}
								}}
								on:blur={() => {
									updateConversationDescription(currentConversation.id, currentConversation.description);
									editingDescriptionId = null;
								}}
								use:focusInput
								class="w-full px-3 py-2 text-sm bg-white dark:bg-gray-800 border border-blue-500 rounded text-gray-900 dark:text-white focus:outline-none"
								placeholder="Add description"
							/>
						{:else}
							<div
								on:click={() => startEditingDescription(currentConversation.id)}
								on:keydown={(e) => {
									if (e.key === 'Enter' || e.key === ' ') {
										startEditingDescription(currentConversation.id);
									}
								}}
								role="button"
								tabindex="0"
								class={`px-3 py-2 rounded cursor-text transition max-w-sm truncate ${
									currentConversation.description
										? 'text-gray-700 dark:text-gray-300 text-sm'
										: 'text-gray-400 dark:text-gray-500 text-sm italic'
								}`}
								title={currentConversation.description || 'Click to add description'}
							>
								{currentConversation.description || 'Click to add description'}
							</div>
						{/if}
					</div>

					<!-- Action Buttons (right side) -->
					<div class="flex items-center gap-2 flex-shrink-0">
						<button
							on:click={toggleResponseModifier}
							class={`px-3 py-1.5 text-xs rounded-lg hover:opacity-90 transition font-medium whitespace-nowrap ${
								(currentConversation?.responseModifier || 'none') === 'chat'
									? 'bg-green-500 text-white'
									: (currentConversation?.responseModifier || 'none') === 'deep'
										? 'bg-blue-500 text-white'
										: 'bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-white'
							}`}
							title={{
								'none': 'No response modifier active. Click to enable Chat mode (brief responses)',
								'chat': 'Chat mode: Brief, conversational responses. Click for Deep mode',
								'deep': 'Deep mode: Comprehensive analysis. Click to disable modifier'
							}[currentConversation?.responseModifier || 'none']}
						>
							<span class="flex items-center gap-1">
								{#if (currentConversation?.responseModifier || 'none') === 'none'}
									<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
									</svg>
									Mod
								{:else if currentConversation?.responseModifier === 'chat'}
									<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
									</svg>
									Chat
								{:else}
									<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
									</svg>
									Deep
								{/if}
							</span>
						</button>
						<button
							on:click={exportConversation}
							disabled={messages.length === 0}
							class="px-3 py-1.5 text-xs bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-white rounded-lg hover:bg-gray-400 dark:hover:bg-gray-500 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition font-medium whitespace-nowrap flex items-center gap-1"
							title="Export chat"
						>
							<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
							</svg>
							Export
						</button>
						<button
							on:click={showClearConvConfirmation}
							disabled={messages.length === 0}
							class="px-3 py-1.5 text-xs bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-white rounded-lg hover:bg-gray-400 dark:hover:bg-gray-500 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition font-medium whitespace-nowrap flex items-center gap-1"
							title="Clear chat"
						>
							<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
							</svg>
							Clear
						</button>
						<button
							on:click={() => (summarizeOpen = true)}
							disabled={messages.length === 0}
							class="px-3 py-1.5 text-xs bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-white rounded-lg hover:bg-gray-400 dark:hover:bg-gray-500 disabled:bg-gray-300 dark:disabled:bg-gray-600 disabled:cursor-not-allowed transition font-medium whitespace-nowrap flex items-center gap-1"
							title="Summarize chat"
						>
							<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
							</svg>
							Summarize
						</button>

						<!-- Quota Label (rightmost) -->
						{#if $isAuthenticated}
							<span 
								class="text-xs font-medium whitespace-nowrap flex items-center gap-1 instant-tooltip tooltip-left {$isQuotaExhausted ? 'text-red-600 dark:text-red-400' : $quotaPercentage >= 80 ? 'text-amber-600 dark:text-amber-400' : 'text-gray-500 dark:text-gray-400'}"
								data-tooltip="Messages used this month"
							>
								{$quota.used}/{$quota.limit}
								{#if $isQuotaExhausted}
									<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
									</svg>
								{/if}
							</span>
						{/if}
					</div>
				</div>
			{/if}

			<!-- Messages Container -->
			<ChatMessages {messages} activeBots={activeBots} />
			
			<!-- Mobile Active Bots (using dedicated mobile component) -->
			<div class="md:hidden">
				<MobileActiveBots
					{activeBots}
					{globalMaxTokens}
					expanded={activeBotsExpanded}
					on:remove={(e) => removeBotFromConversation(e.detail)}
					on:removeAll={removeAllBotsFromConversation}
					on:toggle={toggleActiveBotsExpanded}
					on:edit={(e) => openEditActiveBot(e.detail)}
				/>
			</div>
			
			<!-- Message Input (with bottom padding for mobile nav bar) -->
			<div class="pb-mobile-nav md:pb-0">
				<MessageInput on:send={(e: CustomEvent<string>) => sendMessage(e.detail)} {isLoading} botsCount={activeBots.length} onCancel={cancelMessage} {messages} {activeBots} {globalAttachments} hasOversizedAttachments={hasOversizedAttachments} {hasInvalidActiveBots} bind:currentMessage={currentInputMessage} />
			</div>
			
			<!-- Desktop Active Bots Bar -->
			{#if activeBots.length > 0}
				<div class="hidden md:block border-t border-gray-200 dark:border-gray-700 px-4 py-2 bg-gray-50 dark:bg-gray-700/50">
					<div class="flex items-center gap-2">
						<button
							on:click={toggleActiveBotsExpanded}
							class="flex items-center gap-2 text-xs font-semibold text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100 transition"
						>
							<span>{activeBotsExpanded ? '▼' : '▶'}</span>
							<span>{activeBots.length} active {activeBots.length === 1 ? 'bot' : 'bots'}</span>
						</button>
						{#if activeBotsExpanded}
							<button
								on:click={removeAllBotsFromConversation}
								class="ml-auto px-3 py-1.5 text-xs bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-white rounded-lg hover:bg-gray-400 dark:hover:bg-gray-500 transition font-medium"
								title="Remove all bots"
							>
								Remove All
							</button>
						{/if}
					</div>
					{#if activeBotsExpanded}
						<div class="flex-1 mt-2 pb-1">
							<div class="flex gap-2 flex-wrap">
								{#each activeBots as bot (bot.id)}
									{@const colors = getProviderColor(bot.provider)}
									{@const botValid = isBotModelValid(bot)}
									{@const validationError = validateBotModel(bot.provider, bot.model)}
									<div 
										class="relative group flex items-center gap-1 rounded px-2 py-1 flex-shrink-0 border-2 transition-colors {botValid ? colors.bg : 'bg-red-50 dark:bg-red-900/30'} {botValid ? colors.border : 'border-red-400 dark:border-red-600'}"
										title={botValid ? 'Click to edit' : validationError || 'Model no longer available - click to fix'}
									>
										{#if !botValid}
											<svg class="w-4 h-4 text-red-500 dark:text-red-400 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
												<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
											</svg>
										{/if}
										<button
											on:click={() => openEditActiveBot(bot)}
											class="flex flex-col text-left hover:opacity-80 transition"
										>
											<span class="text-xs font-medium {botValid ? colors.text : 'text-red-700 dark:text-red-300'}">{bot.name || bot.provider}</span>
											<span class="text-[10px] {botValid ? colors.subtext : 'text-red-600 dark:text-red-400 line-through'}">{bot.provider} • {bot.model}</span>
										</button>
										<button
											on:click={() => removeBotFromConversation(bot.id)}
											class="ml-1 text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 text-lg leading-none"
											title="Remove {bot.name || bot.provider}"
										>
											×
										</button>
										<!-- Custom instant tooltip - uses fixed positioning to escape overflow -->
										<div class="fixed z-[9999] invisible group-hover:visible opacity-0 group-hover:opacity-100 pointer-events-none -translate-y-full -translate-x-0 -mt-2"
											 style="top: auto; bottom: auto;">
											<div class="{botValid ? 'bg-gray-900 dark:bg-gray-700' : 'bg-red-900 dark:bg-red-800'} text-white text-xs rounded-lg py-2 px-3 whitespace-nowrap shadow-lg">
												<div class="font-semibold">{bot.name || 'Unnamed Bot'}</div>
												{#if !botValid}
													<div class="text-red-300 mt-1 font-medium">⚠ Model no longer available</div>
													<div class="text-red-200 text-[10px]">Click to update model</div>
												{:else}
													<div class="text-blue-300 text-[10px]">Click to edit</div>
												{/if}
												<div class="text-gray-300 mt-1">Provider: {bot.provider}</div>
												<div class="text-gray-300">Model: {bot.model}</div>
												<div class="text-gray-300">Max Tokens: {bot.maxTokens || globalMaxTokens}</div>
											</div>
										</div>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>
{/if}

<!-- Sign In Modal -->
<SignInModal bind:open={signInOpen} />

<!-- About Modal -->
<AboutModal bind:isOpen={aboutOpen} on:close={() => (aboutOpen = false)} />

<!-- Intro Modal (for new users) -->
<IntroModal bind:isOpen={introOpen} on:ok={handleIntroOk} on:dismiss={handleIntroDismiss} />

<!-- Edit Active Bot Dialog -->
<EditBotDialog
	bot={editingActiveBot}
	bind:isOpen={editBotDialogOpen}
	on:save={handleSaveActiveBot}
	on:cancel={handleCancelEditActiveBot}
/>

<!-- Settings Modal -->
<SettingsModal
	bind:isOpen={settingsOpen}
	apiBase={API_BASE}
	{authHeaders}
	{theme}
	{botCountsByProvider}
	isAuthenticated={$isAuthenticated}
	currentUser={$auth.user}
	bind:globalMaxTokens
	onExportConfig={exportConfig}
	onImportConfig={importConfig}
	on:themeChange={(e) => handleThemeChange(e.detail)}
	on:keysChanged={loadProviderConfig}
	on:keyRemoved={(e) => removeBotsForProvider(e.detail.providerId)}
	on:logout={() => { logout(); settingsOpen = false; }}
	on:close={() => (settingsOpen = false)}
/>

<!-- Summarize Modal -->
<SummarizeModal
	bind:isOpen={summarizeOpen}
	savedBots={bots}
	isLoading={isSummarizing}
	{activeBots}
	on:summarize={(e) => summarizeConversation(e.detail)}
	on:close={() => (summarizeOpen = false)}
/>

<!-- Summary Result Modal -->
<SummaryResultModal
	bind:isOpen={summaryResultOpen}
	{summaryContent}
	botName={selectedSummaryBot?.name}
	botProvider={selectedSummaryBot?.provider}
	botModel={selectedSummaryBot?.model}
	messageCount={messages.length}
	conversationName={currentConversation?.name || ''}
	conversationDescription={currentConversation?.description || ''}
	{participatingBots}
	timestamp={new Date()}
/>

<!-- Remove All Bots Confirmation Modal -->
{#if removeAllConfirmOpen}
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-w-sm">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Remove all bots?</h3>
			<p class="text-gray-600 dark:text-gray-400 mb-6">This will remove all {activeBots.length} {activeBots.length === 1 ? 'bot' : 'bots'} from the chat.</p>
			<div class="flex gap-2 justify-end">
				<button
					on:click={cancelRemoveAllBots}
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition"
				>
					Cancel
				</button>
				<button
					on:click={confirmRemoveAllBots}
					class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition"
				>
					Remove All
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Clear Conversation Confirmation Modal -->
{#if clearConvConfirmOpen}
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-w-sm">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Clear chat?</h3>
			<p class="text-gray-600 dark:text-gray-400 mb-6">This will delete all {messages.length} {messages.length === 1 ? 'message' : 'messages'} from the chat. Your active bots will remain in the chat.</p>
			<div class="flex gap-2 justify-end">
				<button
					on:click={cancelClearConversation}
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-200 dark:bg-gray-700 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition"
				>
					Cancel
				</button>
				<button
					on:click={clearConversation}
					class="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 transition"
				>
					Clear
				</button>
			</div>
		</div>
	</div>
{/if}

{#if duplicateNameErrorOpen}
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-w-sm">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Name already exists</h3>
			<p class="text-gray-600 dark:text-gray-400 mb-6">A chat with this name already exists. Please choose a different name.</p>
			<div class="flex gap-2 justify-end">
				<button
					on:click={() => (duplicateNameErrorOpen = false)}
					class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition"
				>
					OK
				</button>
			</div>
		</div>
	</div>
{/if}

{#if exportModalOpen}
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-w-sm">
			<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Export Chat</h3>
			<p class="text-gray-600 dark:text-gray-400 mb-6">Choose how you'd like to export this chat.</p>
			<div class="flex gap-2 justify-end">
				<button
					on:click={() => (exportModalOpen = false)}
					class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition"
				>
					Cancel
				</button>
				<button
					on:click={exportSave}
					class="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 transition"
				>
					Save
				</button>
				<button
					on:click={exportPrint}
					class="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition"
				>
					Print
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Import Confirmation Modal -->
{#if importConfirmOpen && pendingImportConfig}
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6 max-w-md mx-4">
			<div class="flex items-center gap-3 mb-4">
				<div class="flex-shrink-0 w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
					<svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
					</svg>
				</div>
				<h3 class="text-xl font-semibold text-gray-900 dark:text-white">Import configuration?</h3>
			</div>
			
			<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-4 mb-4">
				<p class="text-sm text-gray-600 dark:text-gray-300 mb-3">This will replace:</p>
				<ul class="space-y-2">
					<li class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
						<span class="w-2 h-2 bg-blue-500 rounded-full"></span>
						{pendingImportConfig.bots.length} {pendingImportConfig.bots.length === 1 ? 'bot' : 'bots'}
					</li>
					<li class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
						<span class="w-2 h-2 bg-purple-500 rounded-full"></span>
						{pendingImportConfig.conversations.length} {pendingImportConfig.conversations.length === 1 ? 'conversation' : 'conversations'}
					</li>
					<li class="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-200">
						<span class="w-2 h-2 bg-green-500 rounded-full"></span>
						{pendingImportConfig.categories?.length || 0} {(pendingImportConfig.categories?.length || 0) === 1 ? 'category' : 'categories'}
					</li>
				</ul>
			</div>
			
			<p class="text-sm text-amber-600 dark:text-amber-400 mb-6 flex items-start gap-2">
				<svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
				</svg>
				<span>Your current data will be overwritten.</span>
			</p>
			
			<div class="flex gap-3 justify-end">
				<button
					on:click={cancelImport}
					class="px-4 py-2.5 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition"
				>
					Cancel
				</button>
				<button
					on:click={confirmImport}
					class="px-4 py-2.5 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition"
				>
					Import
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Import Result Modal -->
{#if importResultOpen}
	<div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
		<div class="bg-white dark:bg-gray-800 rounded-xl shadow-2xl p-6 max-w-sm mx-4">
			<div class="flex flex-col items-center text-center">
				{#if importResultSuccess}
					<div class="w-12 h-12 bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center mb-4">
						<svg class="w-6 h-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
						</svg>
					</div>
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Import Successful</h3>
					<p class="text-gray-600 dark:text-gray-400 mb-2">{importResultMessage}</p>
					<p class="text-sm text-gray-500 dark:text-gray-500 mb-6">The page will refresh to apply changes.</p>
				{:else}
					<div class="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center mb-4">
						<svg class="w-6 h-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</div>
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">Import Failed</h3>
					<p class="text-gray-600 dark:text-gray-400 mb-6">{importResultMessage}</p>
				{/if}
				
				<button
					on:click={closeImportResult}
					class="px-6 py-2.5 text-sm font-medium text-white {importResultSuccess ? 'bg-green-600 hover:bg-green-700' : 'bg-blue-600 hover:bg-blue-700'} rounded-lg transition"
				>
					{importResultSuccess ? 'Continue' : 'OK'}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- ===== MOBILE UI COMPONENTS ===== -->

<!-- Mobile Bottom Navigation (only shown when authenticated) -->
{#if $isAuthenticated}
<MobileNav
	activePanel={mobilePanel}
	{hasConfiguredProviders}
	attachmentCount={globalAttachments.length}
	chatCount={conversations.length}
	on:openPanel={(e) => openMobilePanel(e.detail)}
	on:closePanel={closeMobilePanel}
	on:newChat={() => { createNewConversation(); closeMobilePanel(); }}
/>
{/if}

<!-- Mobile Slide Panels -->

<!-- Bot Library Panel -->
<SlidePanel
	open={mobilePanel === 'library'}
	side="left"
	title="Bot Library"
	on:close={closeMobilePanel}
>
	<div class="p-4">
		<BotLibrary 
			savedBots={bots} 
			canAddToConversation={canAddBotToConversation}
			currentBotsInConversation={activeBots.length}
			maxBotsPerConversation={$tierLimits.maxBotsPerConversation}
			on:add={(e) => { addBotToConversation(e.detail); }} 
			on:delete={(e) => { removeBotFromAll(e.detail); }} 
		/>
	</div>
</SlidePanel>

<!-- Chats Panel -->
<SlidePanel
	open={mobilePanel === 'chats'}
	side="right"
	title="Chats"
	on:close={closeMobilePanel}
>
	<MobileConversationList
		chats={conversations}
		currentChatId={currentConversationId}
		canCreateChat={canCreateConversation}
		maxChats={$tierLimits.maxConversations}
		isStreaming={isStreaming}
		on:select={(e) => handleMobileConversationSelect(e.detail)}
		on:delete={(e) => handleMobileConversationDelete(e.detail)}
		on:rename={(e) => handleMobileConversationRename(e.detail)}
	/>
</SlidePanel>

<!-- New Bot Panel -->
<SlidePanel
	open={mobilePanel === 'newbot'}
	side="left"
	title="Create New Bot"
	on:close={closeMobilePanel}
>
	<div class="p-4">
		<NewBotForm
			on:save={async (e) => {
				const saved = await saveBotConfig(e.detail);
				if (saved) {
					await addBotToConversation(saved);
				}
				closeMobilePanel();
			}}
			on:openSettings={() => { closeMobilePanel(); settingsOpen = true; }}
		/>
	</div>
</SlidePanel>

<!-- Attachments Panel -->
<SlidePanel
	open={mobilePanel === 'attachments'}
	side="bottom"
	title="Attachments"
	on:close={closeMobilePanel}
>
	<div class="p-4">
		<GlobalAttachment bind:files={globalAttachments} bind:hasOversizedFiles={hasOversizedAttachments} />
	</div>
</SlidePanel>

<!-- Close Chat Confirmation Modal -->
<AlertModal
	bind:isOpen={closeChatConfirmOpen}
	title="Close Chat?"
	message="Messages will be lost and bots will be removed from this chat."
	type="warning"
	confirmText="Close Chat"
	cancelText="Cancel"
	showCancel={true}
	on:confirm={executeCloseChat}
	on:cancel={cancelCloseChat}
	on:close={cancelCloseChat}
/>

<!-- Global Alert Modal -->
<AlertModal
	bind:isOpen={alertOpen}
	title={alertTitle}
	message={alertMessage}
	type={alertType}
	on:confirm={() => alertOpen = false}
	on:close={() => alertOpen = false}
/>