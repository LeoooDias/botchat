/**
 * Subscription store for botchat billing.
 * 
 * Tracks subscription status, quota usage, and enforces tier limits.
 * Free tier: 3 conversations, 5 saved bots, 3 bots per conversation, 100 messages/month
 * Paid tier: Unlimited conversations, unlimited bots, 10 bots per conversation, 5000 messages/month
 * BYOK: Unlimited messages (when using own API keys)
 */

import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';
import { isAuthenticated, authToken } from './auth';

// -----------------------------
// Types
// -----------------------------

export type SubscriptionStatus = 'none' | 'active' | 'trialing' | 'past_due' | 'canceled';

export interface QuotaState {
	used: number;
	limit: number;
	remaining: number;
	periodEndsAt: string | null;
	isPaid: boolean;
	isLoading: boolean;
	error: string | null;
}

export interface SubscriptionState {
	status: SubscriptionStatus;
	isLoading: boolean;
	error: string | null;
	endsAt: string | null;
}

export interface TierLimits {
	maxConversations: number;
	maxSavedBots: number;
	maxBotsPerConversation: number;
}

// -----------------------------
// Constants
// -----------------------------

export const FREE_TIER_QUOTA = 100;  // messages per month
export const PAID_TIER_QUOTA = 5000; // messages per month

export const FREE_TIER_LIMITS: TierLimits = {
	maxConversations: 3,
	maxSavedBots: Infinity,  // Unlimited bot library for all users
	maxBotsPerConversation: 3,
};

export const PAID_TIER_LIMITS: TierLimits = {
	maxConversations: Infinity,
	maxSavedBots: Infinity,
	maxBotsPerConversation: 10,
};

// -----------------------------
// Store
// -----------------------------

const initialState: SubscriptionState = {
	status: 'none',
	isLoading: false,
	error: null,
	endsAt: null,
};

function createSubscriptionStore() {
	const { subscribe, set, update } = writable<SubscriptionState>(initialState);

	return {
		subscribe,

		/**
		 * Fetch subscription status from backend.
		 */
		async fetchStatus() {
			const token = get(authToken);
			if (!token) {
				set({ ...initialState, status: 'none' });
				return;
			}

			update(s => ({ ...s, isLoading: true, error: null }));

			try {
				const API_BASE = browser ? (import.meta.env.VITE_API_BASE || 'http://localhost:8000') : '';
				const response = await fetch(`${API_BASE}/billing/status`, {
					headers: {
						'Authorization': `Bearer ${token}`,
					},
				});

				if (!response.ok) {
					throw new Error('Failed to fetch subscription status');
				}

				const data = await response.json();
				set({
					status: data.status || 'none',
					isLoading: false,
					error: null,
					endsAt: data.ends_at || null,
				});
			} catch (error) {
				console.error('Failed to fetch subscription status:', error);
				set({
					status: 'none',
					isLoading: false,
					error: error instanceof Error ? error.message : 'Unknown error',
					endsAt: null,
				});
			}
		},

		/**
		 * Reset to initial state (on logout).
		 */
		reset() {
			set(initialState);
		},
	};
}

export const subscription = createSubscriptionStore();

// -----------------------------
// Quota Store
// -----------------------------

const initialQuotaState: QuotaState = {
	used: 0,
	limit: FREE_TIER_QUOTA,
	remaining: FREE_TIER_QUOTA,
	periodEndsAt: null,
	isPaid: false,
	isLoading: false,
	error: null,
};

function createQuotaStore() {
	const { subscribe, set, update } = writable<QuotaState>(initialQuotaState);

	return {
		subscribe,

		/**
		 * Fetch quota status from backend.
		 */
		async fetchQuota() {
			const token = get(authToken);
			if (!token) {
				set({ ...initialQuotaState });
				return;
			}

			update(s => ({ ...s, isLoading: true, error: null }));

			try {
				const API_BASE = browser ? (import.meta.env.VITE_API_BASE || 'http://localhost:8000') : '';
				const response = await fetch(`${API_BASE}/auth/quota`, {
					headers: {
						'Authorization': `Bearer ${token}`,
					},
				});

				if (!response.ok) {
					throw new Error('Failed to fetch quota status');
				}

				const data = await response.json();
				set({
					used: data.used ?? 0,
					limit: data.limit ?? FREE_TIER_QUOTA,
					remaining: data.remaining ?? FREE_TIER_QUOTA,
					periodEndsAt: data.period_ends_at ?? null,
					isPaid: data.is_paid ?? false,
					isLoading: false,
					error: null,
				});
			} catch (error) {
				console.error('Failed to fetch quota status:', error);
				update(s => ({
					...s,
					isLoading: false,
					error: error instanceof Error ? error.message : 'Unknown error',
				}));
			}
		},

		/**
		 * Optimistically increment used count (after sending message).
		 * Used for immediate UI feedback before server confirms.
		 */
		incrementUsed(count: number = 1) {
			update(s => ({
				...s,
				used: s.used + count,
				remaining: Math.max(0, s.remaining - count),
			}));
		},

		/**
		 * Set quota state directly (for real-time updates from SSE).
		 */
		setQuota(quotaData: Partial<QuotaState>) {
			update(s => ({
				...s,
				...quotaData,
				isLoading: false,
				error: null,
			}));
		},

		/**
		 * Reset to initial state (on logout).
		 */
		reset() {
			set(initialQuotaState);
		},
	};
}

export const quota = createQuotaStore();

// -----------------------------
// Derived Stores
// -----------------------------

/**
 * Whether the user has an active paid subscription.
 */
export const isPaidUser = derived(subscription, ($sub) => {
	return $sub.status === 'active' || $sub.status === 'trialing';
});

/**
 * Current tier limits based on subscription status.
 */
export const tierLimits = derived(isPaidUser, ($isPaid) => {
	return $isPaid ? PAID_TIER_LIMITS : FREE_TIER_LIMITS;
});

/**
 * Human-readable tier name.
 */
export const tierName = derived(isPaidUser, ($isPaid) => {
	return $isPaid ? 'Paid' : 'Free';
});

/**
 * Whether user has exceeded their quota.
 */
export const isQuotaExhausted = derived(quota, ($quota) => {
	return $quota.remaining <= 0;
});

/**
 * Percentage of quota used (0-100).
 */
export const quotaPercentage = derived(quota, ($quota) => {
	if ($quota.limit === 0) return 100;
	return Math.min(100, Math.round(($quota.used / $quota.limit) * 100));
});

/**
 * Human-readable quota status.
 */
export const quotaStatus = derived(quota, ($quota) => {
	return `${$quota.used.toLocaleString()} / ${$quota.limit.toLocaleString()} messages`;
});
