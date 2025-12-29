/**
 * Provider configuration store for botchat.
 * 
 * Tracks which AI providers the user has configured with API keys.
 * Components use this to filter available options and clean up bots
 * when providers are removed.
 * 
 * Note: API keys are stored encrypted in localStorage, not on the server.
 * This store queries the server for provider metadata (names, docs links)
 * but checks localStorage for configured status.
 */

import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';
import { hasProviderKey, getMaskedKey, getConfiguredProviders } from '$lib/utils/keyEncryption';

export interface ProviderInfo {
	id: string;
	display_name: string;
	configured: boolean;
	source: string | null;
	masked_key: string | null;
}

interface ProvidersState {
	providers: Record<string, ProviderInfo>;
	loading: boolean;
	error: string | null;
	lastFetched: number | null;
}

const initialState: ProvidersState = {
	providers: {},
	loading: false,
	error: null,
	lastFetched: null
};

function createProvidersStore() {
	const { subscribe, set, update } = writable<ProvidersState>(initialState);

	return {
		subscribe,

		/**
		 * Load provider configuration from the backend + localStorage.
		 * Server provides metadata (names, docs), localStorage has configured status.
		 */
		async load(apiBase: string, authHeaders: () => Record<string, string>) {
			update(state => ({ ...state, loading: true, error: null }));

			try {
				const response = await fetch(`${apiBase}/settings/providers`, {
					headers: authHeaders()
				});

				if (!response.ok) {
					throw new Error(`Failed to load providers: ${response.status}`);
				}

				const data: Record<string, Omit<ProviderInfo, 'id'>> = await response.json();

				// Convert to state with IDs, checking localStorage for configured status
				const providers: Record<string, ProviderInfo> = {};
				for (const [id, info] of Object.entries(data)) {
					// Check localStorage for this provider's key
					const hasLocalKey = browser && hasProviderKey(id);
					const maskedKey = hasLocalKey ? getMaskedKey(id) : null;
					
					providers[id] = { 
						id, 
						...info,
						// Override with localStorage status
						configured: hasLocalKey,
						source: hasLocalKey ? 'local' : null,
						masked_key: maskedKey
					};
				}

				update(state => ({
					...state,
					providers,
					loading: false,
					lastFetched: Date.now()
				}));

				return providers;
			} catch (e) {
				const error = e instanceof Error ? e.message : 'Failed to load providers';
				update(state => ({ ...state, loading: false, error }));
				throw e;
			}
		},

		/**
		 * Mark a provider as configured after key is saved to localStorage.
		 */
		markConfigured(providerId: string, maskedKey: string) {
			update(state => {
				if (state.providers[providerId]) {
					state.providers[providerId] = {
						...state.providers[providerId],
						configured: true,
						source: 'local',
						masked_key: maskedKey
					};
				}
				return { ...state };
			});
		},

		/**
		 * Mark a provider as unconfigured after key is removed.
		 */
		markUnconfigured(providerId: string) {
			update(state => {
				if (state.providers[providerId]) {
					state.providers[providerId] = {
						...state.providers[providerId],
						configured: false,
						source: null,
						masked_key: null
					};
				}
				return { ...state };
			});
		},

		/**
		 * Get current state synchronously.
		 */
		getState() {
			return get({ subscribe });
		},

		/**
		 * Reset the store.
		 */
		reset() {
			set(initialState);
		}
	};
}

export const providersStore = createProvidersStore();

/**
 * Derived store: list of configured provider IDs.
 */
export const configuredProviderIds = derived(
	providersStore,
	$state => Object.values($state.providers)
		.filter(p => p.configured)
		.map(p => p.id)
);

/**
 * Derived store: check if a specific provider is configured.
 */
export function isProviderConfigured(providerId: string): boolean {
	const state = providersStore.getState();
	return state.providers[providerId]?.configured ?? false;
}

/**
 * Get display name for a provider.
 */
export function getProviderDisplayName(providerId: string): string {
	const names: Record<string, string> = {
		openai: 'OpenAI',
		anthropic: 'Anthropic',
		gemini: 'Google (Gemini)'
	};
	return names[providerId] || providerId;
}
