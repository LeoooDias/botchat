/**
 * User-namespaced localStorage utility.
 * 
 * Ensures each user's data (bots, conversations, settings) is isolated
 * from other users who may use the same browser.
 * 
 * Keys are namespaced as: botchat_{userId}_{key}
 * 
 * Global keys (not user-specific): theme, botchat_auth
 */

import { browser } from '$app/environment';
import { get } from 'svelte/store';
import { auth } from '$lib/stores/auth';

// Keys that should be namespaced per user
const USER_KEYS = [
    'savedBots',
    'conversations',
    'currentConversationId',
    'botCategories',
    'collapsedCategories',
    'botLibraryInfoDismissed',
    'globalMaxTokens',
    'botchat_encrypted_keys',
    'botchat_encryption_key_hash',
    'starterConfigInitialized',
    'introModalDismissed',
] as const;

// Keys that remain global (shared across users)
const GLOBAL_KEYS = [
    'theme',
    'botchat_auth',
] as const;

type UserKey = typeof USER_KEYS[number];
type GlobalKey = typeof GLOBAL_KEYS[number];

/**
 * Get the current user's ID for namespacing.
 * Uses provider + id to create a unique identifier.
 */
export function getCurrentUserId(): string | null {
    if (!browser) return null;
    
    const authState = get(auth);
    if (!authState.isAuthenticated || !authState.user) return null;
    
    // Create a unique ID from provider + user id
    return `${authState.user.provider}_${authState.user.id}`;
}

/**
 * Get the namespaced key for user-specific data.
 */
function getNamespacedKey(key: UserKey, userId: string): string {
    return `botchat_${userId}_${key}`;
}

/**
 * Get item from user-namespaced localStorage.
 * Returns null if no user is authenticated or key doesn't exist.
 */
export function getUserItem(key: UserKey): string | null {
    if (!browser) return null;
    
    const userId = getCurrentUserId();
    if (!userId) return null;
    
    return localStorage.getItem(getNamespacedKey(key, userId));
}

/**
 * Set item in user-namespaced localStorage.
 * Does nothing if no user is authenticated.
 */
export function setUserItem(key: UserKey, value: string): void {
    if (!browser) return;
    
    const userId = getCurrentUserId();
    if (!userId) return;
    
    localStorage.setItem(getNamespacedKey(key, userId), value);
}

/**
 * Remove item from user-namespaced localStorage.
 */
export function removeUserItem(key: UserKey): void {
    if (!browser) return;
    
    const userId = getCurrentUserId();
    if (!userId) return;
    
    localStorage.removeItem(getNamespacedKey(key, userId));
}

/**
 * Get item from global localStorage (not user-specific).
 */
export function getGlobalItem(key: GlobalKey): string | null {
    if (!browser) return null;
    return localStorage.getItem(key);
}

/**
 * Set item in global localStorage (not user-specific).
 */
export function setGlobalItem(key: GlobalKey, value: string): void {
    if (!browser) return;
    localStorage.setItem(key, value);
}

/**
 * Migrate data from old non-namespaced keys to user-namespaced keys.
 * Called once when a user first signs in after this update.
 * 
 * Migration strategy:
 * - Check if user already has namespaced data
 * - If not, and old global data exists, migrate it
 * - Mark migration as complete for this user
 */
export function migrateUserData(): { migrated: boolean; keys: string[] } {
    if (!browser) return { migrated: false, keys: [] };
    
    const userId = getCurrentUserId();
    if (!userId) return { migrated: false, keys: [] };
    
    const migrationKey = `botchat_${userId}_migrated`;
    
    // Check if already migrated
    if (localStorage.getItem(migrationKey)) {
        return { migrated: false, keys: [] };
    }
    
    const migratedKeys: string[] = [];
    
    // Migrate each user key if old data exists and new doesn't
    for (const key of USER_KEYS) {
        const oldValue = localStorage.getItem(key);
        const newKey = getNamespacedKey(key, userId);
        const newValue = localStorage.getItem(newKey);
        
        // Only migrate if old exists and new doesn't
        if (oldValue && !newValue) {
            localStorage.setItem(newKey, oldValue);
            migratedKeys.push(key);
            console.log(`[UserStorage] Migrated ${key} for user ${userId}`);
        }
    }
    
    // Mark migration complete
    localStorage.setItem(migrationKey, Date.now().toString());
    
    if (migratedKeys.length > 0) {
        console.log(`[UserStorage] Migration complete for user ${userId}: ${migratedKeys.join(', ')}`);
    }
    
    return { migrated: migratedKeys.length > 0, keys: migratedKeys };
}

/**
 * Clear all user-specific data (for testing or account reset).
 */
export function clearUserData(): void {
    if (!browser) return;
    
    const userId = getCurrentUserId();
    if (!userId) return;
    
    for (const key of USER_KEYS) {
        localStorage.removeItem(getNamespacedKey(key, userId));
    }
    
    // Also clear migration flag
    localStorage.removeItem(`botchat_${userId}_migrated`);
    
    console.log(`[UserStorage] Cleared all data for user ${userId}`);
}
