<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	import { providersStore } from '$lib/stores/providers';
	import { 
		saveProviderKey, 
		deleteProviderKey, 
		hasProviderKey, 
		getMaskedKey,
		getConfiguredProviders 
	} from '$lib/utils/keyEncryption';
	import AlertModal from './AlertModal.svelte';

	const dispatch = createEventDispatcher<{
		keysChanged: void;
		keyRemoved: { providerId: string; providerName: string };
		close: void;
		themeChange: 'light' | 'dark';
		logout: void;
	}>();

	export let isOpen = false;
	export let apiBase: string;
	export let authHeaders: () => Record<string, string>;
	export let theme: 'light' | 'dark' = 'light';
	export let globalMaxTokens = 4000;
	export let onExportConfig: (() => void) | null = null;
	export let onImportConfig: (() => void) | null = null;
	export let isAuthenticated = false;  // Whether user is signed in
	
	// Count of bots using each provider (passed from parent)
	export let botCountsByProvider: Record<string, number> = {};
	
	// Delete confirmation modal state
	let deleteConfirmOpen = false;
	let pendingDeleteProviderId: string | null = null;
	let deleteWarningMessage = '';
	let deleteWarningTitle = '';
	
	// Encryption key from server (fetched on mount when authenticated)
	let encryptionKey: string | null = null;
	
	// Advanced section (API keys) toggle state
	let showAdvanced = false;


	interface ProviderInfo {
		display_name: string;
		configured: boolean;
		source: string | null;
		masked_key: string | null;
		docs_url: string;
		key_prefix: string;
	}

	interface ProviderState extends ProviderInfo {
		id: string;
		inputKey: string;
		status: 'idle' | 'verifying' | 'saving' | 'success' | 'error';
		message: string;
	}

	let providers: Record<string, ProviderState> = {};
	let loading = true;
	let error: string | null = null;

	function handleThemeChange(newTheme: 'light' | 'dark') {
		theme = newTheme;
		dispatch('themeChange', newTheme);
	}

	// Fetch encryption key when modal opens (if authenticated)
	async function fetchEncryptionKey(): Promise<string | null> {
		if (encryptionKey) return encryptionKey;
		
		try {
			const response = await fetch(`${apiBase}/auth/encryption-key`, {
				credentials: 'include',
				headers: authHeaders()
			});
			
			if (response.ok) {
				const data = await response.json();
				encryptionKey = data.encryption_key;
				return encryptionKey;
			}
		} catch (e) {
			console.error('Failed to fetch encryption key:', e);
		}
		return null;
	}

	// Load providers when modal opens
	$: if (isOpen) {
		loadProviders();
	}

	async function loadProviders() {
		loading = true;
		error = null;

		try {
			// Fetch encryption key first
			await fetchEncryptionKey();
			
			// Get provider metadata from server (just the list of supported providers)
			const response = await fetch(`${apiBase}/settings/providers`, {
				headers: authHeaders()
			});

			if (!response.ok) {
				throw new Error(`Failed to load providers: ${response.status}`);
			}

			const data: Record<string, ProviderInfo> = await response.json();

			// Convert to state objects, checking localStorage for configured status
			providers = {};
			for (const [id, info] of Object.entries(data)) {
				// Check localStorage for this provider's key
				const hasLocalKey = hasProviderKey(id);
				const maskedKey = hasLocalKey ? getMaskedKey(id) : null;
				
				providers[id] = {
					id,
					...info,
					// Override with localStorage status
					configured: hasLocalKey,
					source: hasLocalKey ? 'local' : null,
					masked_key: maskedKey,
					inputKey: '',
					status: 'idle',
					message: hasLocalKey ? 'Stored locally (encrypted)' : 'Not configured'
				};
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load providers';
		} finally {
			loading = false;
		}
	}

	async function verifyKey(providerId: string) {
		const provider = providers[providerId];
		if (!provider.inputKey.trim()) return;

		provider.status = 'verifying';
		provider.message = 'Verifying...';
		providers = providers; // Trigger reactivity

		try {
			const response = await fetch(`${apiBase}/settings/keys/verify`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					...authHeaders()
				},
				body: JSON.stringify({
					provider: providerId,
					api_key: provider.inputKey
				})
			});

			const result = await response.json();

			if (result.valid) {
				provider.status = 'success';
				provider.message = result.message;
			} else {
				provider.status = 'error';
				provider.message = result.message || 'Invalid key';
			}
		} catch (e) {
			provider.status = 'error';
			provider.message = 'Connection error';
		}

		providers = providers;
	}

	async function saveKey(providerId: string) {
		const provider = providers[providerId];
		if (!provider.inputKey.trim()) return;

		provider.status = 'saving';
		provider.message = 'Encrypting and saving...';
		providers = providers;

		try {
			// Get encryption key from server
			const key = await fetchEncryptionKey();
			if (!key) {
				provider.status = 'error';
				provider.message = 'Not authenticated. Please sign in.';
				providers = providers;
				return;
			}
			
			// Encrypt and save to localStorage
			const { masked } = await saveProviderKey(providerId, provider.inputKey, key);
			
			provider.status = 'success';
			provider.message = 'Saved locally (encrypted)';
			provider.configured = true;
			provider.source = 'local';
			provider.masked_key = masked;
			provider.inputKey = '';
			
			// Update the providers store
			providersStore.markConfigured(providerId, masked);
			
			dispatch('keysChanged');
		} catch (e) {
			provider.status = 'error';
			provider.message = e instanceof Error ? e.message : 'Failed to save';
		}

		providers = providers;
	}

	async function deleteKey(providerId: string) {
		const provider = providers[providerId];
		const botCount = botCountsByProvider[providerId] || 0;

		// Build warning message
		if (botCount > 0) {
			deleteWarningTitle = `Remove ${provider.display_name} API Key?`;
			deleteWarningMessage = `This will:\n\n` +
				`• Remove ${botCount} bot${botCount > 1 ? 's' : ''} from your saved library\n` +
				`• Remove those bots from all chats\n` +
				`• Delete any messages from those bots\n\n` +
				`This cannot be undone.\n\n` +
				`💡 To rotate your key instead, cancel and enter a new key above.`;
		} else {
			deleteWarningTitle = `Remove ${provider.display_name} API Key?`;
			deleteWarningMessage = `💡 Tip: To rotate your key, just enter a new one above — no need to delete first.`;
		}

		pendingDeleteProviderId = providerId;
		deleteConfirmOpen = true;
	}

	async function confirmDeleteKey() {
		if (!pendingDeleteProviderId) return;
		
		const providerId = pendingDeleteProviderId;
		const provider = providers[providerId];

		try {
			// Delete from localStorage
			deleteProviderKey(providerId);
			
			provider.configured = false;
			provider.source = null;
			provider.masked_key = null;
			provider.status = 'idle';
			provider.message = 'Not configured';
			
			// Update the providers store
			providersStore.markUnconfigured(providerId);
			
			// Dispatch events
			dispatch('keysChanged');
			dispatch('keyRemoved', { providerId, providerName: provider.display_name });
		} catch (e) {
			provider.status = 'error';
			provider.message = 'Failed to delete';
		}

		providers = providers;
		pendingDeleteProviderId = null;
	}

	function close() {
		isOpen = false;
		dispatch('close');
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'success':
				return 'text-green-500';
			case 'error':
				return 'text-red-500';
			case 'verifying':
			case 'saving':
				return 'text-yellow-500';
			default:
				return 'text-gray-500';
		}
	}

	function getStatusIcon(status: string, configured: boolean): string {
		if (status === 'verifying' || status === 'saving') return '⏳';
		if (status === 'success' || configured) return '✓';
		if (status === 'error') return '✗';
		return '○';
	}
</script>

<svelte:window onkeydown={(e) => isOpen && e.key === 'Escape' && close()} />

{#if isOpen}
	<!-- Backdrop -->
	<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
	<div
		class="fixed inset-0 bg-black/50 z-40"
		onclick={close}
	></div>

	<!-- Modal (full-screen on mobile, centered on desktop) -->
	<div class="fixed inset-0 flex items-center justify-center z-50 md:p-4 pointer-events-none">
		<div
			class="bg-white dark:bg-gray-800 md:rounded-xl shadow-2xl w-full h-full md:h-auto md:max-w-lg md:max-h-[90vh] overflow-hidden flex flex-col pointer-events-auto safe-top"
			role="dialog"
			aria-modal="true"
			aria-labelledby="settings-title"
		>
			<!-- Header -->
			<div class="flex items-center justify-between p-4 border-b dark:border-gray-700">
				<h2 id="settings-title" class="text-xl font-semibold dark:text-white flex items-center gap-2">
					<svg class="w-6 h-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
						<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
					</svg>
					Settings
				</h2>
				<button
					onclick={close}
					class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors touch-target"
					aria-label="Close"
				>
					<svg class="w-6 h-6 dark:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>

			<!-- Content -->
			<div class="flex-1 overflow-y-auto p-4 space-y-6 mobile-scroll pb-safe">
				<!-- Theme Selection -->
				<div>
					<h3 class="text-lg font-medium mb-2 dark:text-white">Theme</h3>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Choose your preferred appearance.
					</p>
					<div class="flex gap-3">
						<button
							onclick={() => handleThemeChange('light')}
							class="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all {theme === 'light' ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30' : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'}"
						>
							<svg class="w-5 h-5 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
								<path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clip-rule="evenodd" />
							</svg>
							<span class="font-medium dark:text-white">Light</span>
						</button>
						<button
							onclick={() => handleThemeChange('dark')}
							class="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-lg border-2 transition-all {theme === 'dark' ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30' : 'border-gray-200 dark:border-gray-600 hover:border-gray-300 dark:hover:border-gray-500'}"
						>
							<svg class="w-5 h-5 text-indigo-400" fill="currentColor" viewBox="0 0 20 20">
								<path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
							</svg>
							<span class="font-medium dark:text-white">Dark</span>
						</button>
					</div>
				</div>

				<hr class="dark:border-gray-700" />

				<!-- Global Max Tokens Setting -->
				<div>
					<h3 class="text-lg font-medium mb-2 dark:text-white">Default Token Limit</h3>
					<p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
						Maximum tokens for API responses. Higher values reduce truncation in long chats (each bot can override).
					</p>
					<div class="flex items-center gap-3">
						<input
							type="range"
							min="500"
							max="10000"
							step="500"
							bind:value={globalMaxTokens}
							class="flex-1 h-2 bg-gray-200 dark:bg-gray-600 rounded-lg appearance-none cursor-pointer accent-blue-500"
						/>
						<div class="flex items-center gap-2 bg-gray-50 dark:bg-gray-700 rounded-lg px-3 py-2 min-w-fit">
							<input
								type="number"
								bind:value={globalMaxTokens}
								min="500"
								max="10000"
								step="500"
								class="w-16 text-center bg-transparent dark:text-white font-medium focus:outline-none"
							/>
							<span class="text-sm text-gray-500 dark:text-gray-400">tokens</span>
						</div>
					</div>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">
						Current: {globalMaxTokens} tokens
					</p>
				</div>

				<hr class="dark:border-gray-700" />

				<!-- Advanced Section (API Keys) -->
				<div>
					<button
						onclick={() => showAdvanced = !showAdvanced}
						class="flex items-center justify-between w-full text-left"
					>
						<h3 class="text-lg font-medium dark:text-white">Advanced</h3>
						<svg 
							class="w-5 h-5 text-gray-500 dark:text-gray-400 transition-transform {showAdvanced ? 'rotate-180' : ''}"
							fill="none" 
							viewBox="0 0 24 24" 
							stroke="currentColor"
						>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
						</svg>
					</button>
					<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
						Bring your own API keys for unlimited messages
					</p>
				</div>
				
				{#if showAdvanced}
					<!-- API Keys Section -->
					<div class="mt-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
						<h4 class="text-md font-medium mb-2 dark:text-white">API Keys (BYOK)</h4>
						<p class="text-sm text-gray-600 dark:text-gray-400 mb-4">
							Bring your own AI provider API keys for unlimited messages. Keys are encrypted and stored locally in your browser. Your keys are never stored on botchat servers.
						</p>
						{#if !isAuthenticated}
							<div class="bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 rounded-lg p-3 mb-4">
								<p class="text-sm text-amber-800 dark:text-amber-200 flex items-center gap-2">
									<svg class="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
									</svg>
									<span><strong>Sign in required</strong> — You must be signed in to save API keys.</span>
								</p>
							</div>
						{/if}
					</div>

					{#if loading}
					<div class="text-center py-8 text-gray-500 dark:text-gray-400">Loading providers...</div>
				{:else if error && isAuthenticated}
					<div class="text-center py-8 text-red-500">{error}</div>
				{:else}
					{#each Object.values(providers) as provider (provider.id)}
						<div class="border dark:border-gray-700 rounded-lg p-4 space-y-3">
							<div class="flex items-center justify-between">
								<div class="flex items-center gap-2">
									<span
										class="text-lg {provider.configured
											? 'text-green-500'
											: 'text-gray-400'}"
									>
										{getStatusIcon(provider.status, provider.configured)}
									</span>
									<span class="font-medium dark:text-white">{provider.display_name}</span>
								</div>
								<a
									href={provider.docs_url}
									target="_blank"
									rel="noopener noreferrer"
									class="text-sm text-blue-600 dark:text-blue-400 hover:underline"
								>
									Get key →
								</a>
							</div>

							{#if provider.configured}
								<div
									class="flex items-center justify-between bg-gray-50 dark:bg-gray-700 rounded px-3 py-2"
								>
									<span class="text-sm font-mono text-gray-600 dark:text-gray-300">
										{provider.masked_key}
									</span>
									<button
										onclick={() => deleteKey(provider.id)}
										class="text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300"
									>
										Remove
									</button>
								</div>
							{/if}

							<div class="flex gap-2">
								<input
									type="password"
									bind:value={provider.inputKey}
									disabled={!isAuthenticated}
									placeholder={!isAuthenticated 
										? 'Sign in to configure'
										: provider.configured
											? 'Enter new key to replace'
											: `${provider.key_prefix}...`}
									class="flex-1 px-3 py-2 border dark:border-gray-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white dark:placeholder-gray-400 disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-100 dark:disabled:bg-gray-800"
									onkeydown={(e) => e.key === 'Enter' && isAuthenticated && saveKey(provider.id)}
								/>
								<button
									onclick={() => verifyKey(provider.id)}
									disabled={!isAuthenticated || !provider.inputKey.trim() ||
										provider.status === 'verifying'}
									class="px-3 py-2 text-sm border dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 dark:text-white disabled:opacity-50 disabled:cursor-not-allowed"
								>
									Test
								</button>
								<button
									onclick={() => saveKey(provider.id)}
									disabled={!isAuthenticated || !provider.inputKey.trim() ||
										provider.status === 'saving'}
									class="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
								>
									Save
								</button>
							</div>

							<p class="text-xs {getStatusColor(provider.status)}">
								{provider.message}
							</p>
						</div>
					{/each}
				{/if}
				{/if} <!-- End showAdvanced -->

				<!-- Import/Export Configuration -->
				<div class="pt-6 border-t dark:border-gray-700">
					<p class="text-xs font-semibold text-gray-700 dark:text-gray-400 mb-3">Configuration</p>
					<div class="flex gap-2">
						<button
							onclick={onImportConfig}
							disabled={!onImportConfig}
							class="flex-1 px-3 py-2 text-xs font-medium text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-1"
							style="background-color: #1f3d99;"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
							</svg>
							Import
						</button>
						<button
							onclick={onExportConfig}
							disabled={!onExportConfig}
							class="flex-1 px-3 py-2 text-xs font-medium text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-1"
							style="background-color: #1f3d99;"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
							</svg>
							Export
						</button>
					</div>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">Export/import bots, categories, and chat settings. Messages are not included.</p>
				</div>
			</div>

			<!-- Footer -->
			<div class="p-4 border-t dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
				<!-- Sign Out -->
				{#if isAuthenticated}
					<div class="mb-4">
						<button
							onclick={() => dispatch('logout')}
							class="w-full px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 transition flex items-center justify-center gap-2"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
							</svg>
							Sign Out
						</button>
					</div>
				{/if}
				<p class="text-xs text-gray-500 dark:text-gray-400 text-center flex items-center justify-center gap-1">
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" />
					</svg>
					Keys are encrypted with AES-256 and stored locally on this machine.
				</p>
			</div>
		</div>
	</div>
{/if}

<!-- Delete Key Confirmation Modal -->
<AlertModal
	bind:isOpen={deleteConfirmOpen}
	title={deleteWarningTitle}
	message={deleteWarningMessage}
	type="warning"
	confirmText="Remove Key"
	cancelText="Cancel"
	showCancel={true}
	on:confirm={confirmDeleteKey}
	on:close={() => { deleteConfirmOpen = false; pendingDeleteProviderId = null; }}
/>
