/**
 * Authentication store and utilities for botchat.
 * 
 * Handles OAuth flow, JWT storage, and user state.
 * Uses localStorage for persistence (privacy-first: no server-side user data).
 */

import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';

// -----------------------------
// Types
// -----------------------------

export interface User {
	provider: 'github' | 'google' | 'dev';
	id: string;
	email: string | null;
	name: string | null;
	avatar: string | null;
}

export interface AuthState {
	isAuthenticated: boolean;
	isLoading: boolean;
	user: User | null;
	token: string | null;
	expiresAt: number | null;
	error: string | null;
}

// -----------------------------
// Store
// -----------------------------

const initialState: AuthState = {
	isAuthenticated: false,
	isLoading: true,
	user: null,
	token: null,
	expiresAt: null,
	error: null,
};

function createAuthStore() {
	const { subscribe, set, update } = writable<AuthState>(initialState);

	// Load from localStorage on init (browser only)
	if (browser) {
		const stored = localStorage.getItem('botchat_auth');
		if (stored) {
			try {
				const parsed = JSON.parse(stored);
				// Check if token is expired
				if (parsed.expiresAt && parsed.expiresAt > Date.now() / 1000) {
					set({
						...parsed,
						isLoading: false,
					});
				} else {
					// Token expired, clear it
					localStorage.removeItem('botchat_auth');
					set({ ...initialState, isLoading: false });
				}
			} catch {
				localStorage.removeItem('botchat_auth');
				set({ ...initialState, isLoading: false });
			}
		} else {
			set({ ...initialState, isLoading: false });
		}
	}

	return {
		subscribe,
		
		/**
		 * Set authenticated state after successful OAuth flow.
		 */
		setAuthenticated: (token: string, user: User, expiresAt: number) => {
			const state: AuthState = {
				isAuthenticated: true,
				isLoading: false,
				user,
				token,
				expiresAt,
				error: null,
			};
			set(state);
			if (browser) {
				localStorage.setItem('botchat_auth', JSON.stringify(state));
			}
		},

		/**
		 * Clear authentication (logout).
		 */
		logout: () => {
			set({ ...initialState, isLoading: false });
			if (browser) {
				localStorage.removeItem('botchat_auth');
			}
		},

		/**
		 * Set loading state.
		 */
		setLoading: (isLoading: boolean) => {
			update(s => ({ ...s, isLoading }));
		},

		/**
		 * Set error state.
		 */
		setError: (error: string) => {
			update(s => ({ ...s, error, isLoading: false }));
		},

		/**
		 * Clear error.
		 */
		clearError: () => {
			update(s => ({ ...s, error: null }));
		},

		/**
		 * Check if token is expired and logout if so.
		 */
		checkExpiry: () => {
			update(s => {
				if (s.expiresAt && s.expiresAt < Date.now() / 1000) {
					if (browser) {
						localStorage.removeItem('botchat_auth');
					}
					return { ...initialState, isLoading: false };
				}
				return s;
			});
		},
	};
}

export const auth = createAuthStore();

// Derived stores for convenience
export const isAuthenticated = derived(auth, $auth => $auth.isAuthenticated);
export const currentUser = derived(auth, $auth => $auth.user);
export const authToken = derived(auth, $auth => $auth.token);
export const authLoading = derived(auth, $auth => $auth.isLoading);
export const authError = derived(auth, $auth => $auth.error);

// Check if session is valid (authenticated AND not expired)
export const isSessionValid = derived(auth, $auth => {
	if (!$auth.isAuthenticated || !$auth.token) return false;
	if (!$auth.expiresAt) return false;
	// Add 60 second buffer to avoid edge cases
	return $auth.expiresAt > (Date.now() / 1000) + 60;
});

// -----------------------------
// OAuth Utilities
// Use actual backend API URL for cross-origin requests
// CORS must be properly configured on backend
// -----------------------------

const API_BASE = (browser && (import.meta.env.VITE_API_BASE as string)) || 'http://localhost:8000';

/**
 * Get OAuth authorization URL for a provider.
 */
export async function getAuthUrl(provider: 'github' | 'google'): Promise<string> {
	const redirectUri = `${window.location.origin}/auth/callback`;
	console.log(`[Auth] getAuthUrl for ${provider}, redirect_uri: ${redirectUri}`);
	
	const response = await fetch(`${API_BASE}/auth/url`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ provider, redirect_uri: redirectUri }),
	});

	console.log(`[Auth] getAuthUrl response status: ${response.status}`);
	if (!response.ok) {
		const error = await response.json();
		console.error(`[Auth] getAuthUrl error:`, error);
		throw new Error(error.detail || 'Failed to get auth URL');
	}

	const data = await response.json();
	console.log(`[Auth] getAuthUrl success, got URL`);
	return data.url;
}

/**
 * Exchange OAuth code for JWT token.
 */
export async function exchangeCode(
	code: string,
	provider: 'github' | 'google'
): Promise<{ token: string; user: User; expiresAt: number }> {
	const redirectUri = `${window.location.origin}/auth/callback`;

	const response = await fetch(`${API_BASE}/auth/callback`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ code, provider, redirect_uri: redirectUri }),
	});

	if (!response.ok) {
		const error = await response.json();
		throw new Error(error.detail || 'Authentication failed');
	}

	const data = await response.json();
	return {
		token: data.token,
		user: data.user,
		expiresAt: data.expires_at,
	};
}

/**
 * Start OAuth flow by redirecting to provider.
 */
export async function startOAuthFlow(provider: 'github' | 'google'): Promise<void> {
	console.log(`[Auth] Starting ${provider} OAuth flow`);
	auth.setLoading(true);
	auth.clearError();
	
	try {
		console.log(`[Auth] Fetching auth URL from API_BASE: ${API_BASE}`);
		const url = await getAuthUrl(provider);
		console.log(`[Auth] Got OAuth URL:`, url);
		// Store provider for callback
		if (browser) {
			sessionStorage.setItem('oauth_provider', provider);
			console.log(`[Auth] Redirecting to:`, url);
		}
		// Redirect to OAuth provider
		window.location.href = url;
	} catch (error) {
		console.error(`[Auth] Error:`, error);
		auth.setError(error instanceof Error ? error.message : 'Failed to start auth');
	}
}

/**
 * Complete OAuth flow after redirect back.
 * Call this from the callback page.
 */
export async function completeOAuthFlow(code: string): Promise<boolean> {
	auth.setLoading(true);
	auth.clearError();

	const provider = browser ? (sessionStorage.getItem('oauth_provider') as 'github' | 'google') : null;
	if (!provider) {
		auth.setError('OAuth session expired. Please try again.');
		return false;
	}

	try {
		const { token, user, expiresAt } = await exchangeCode(code, provider);
		auth.setAuthenticated(token, user, expiresAt);
		
		// Clean up
		if (browser) {
			sessionStorage.removeItem('oauth_provider');
		}
		
		return true;
	} catch (error) {
		auth.setError(error instanceof Error ? error.message : 'Authentication failed');
		return false;
	}
}

/**
 * Get authorization headers for API requests.
 * Returns Bearer token if authenticated and not expired, empty object otherwise.
 * Auto-logs out if token is expired.
 */
export function getAuthHeaders(): Record<string, string> {
	const state = get(auth);
	if (state.token && state.expiresAt) {
		// Check if token is expired (with 60 second buffer)
		if (state.expiresAt > (Date.now() / 1000) + 60) {
			return { Authorization: `Bearer ${state.token}` };
		} else {
			// Token expired, auto-logout
			auth.logout();
			return {};
		}
	}
	return {};
}

/**
 * Logout and clear all auth state.
 */
export function logout(): void {
	auth.logout();
}
