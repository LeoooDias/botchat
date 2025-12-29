/**
 * Client-side encryption for AI provider API keys.
 * 
 * Uses Web Crypto API (AES-GCM) for secure encryption.
 * Keys are stored encrypted in localStorage, decrypted only when needed.
 * The encryption key is stored server-side per user (never the actual API keys).
 * 
 * Security model:
 * - Encrypted API keys in localStorage (useless without encryption key)
 * - Encryption key in server database (useless without encrypted data)
 * - Both needed to decrypt = protection against single-point breach
 * 
 * User isolation:
 * - Keys are namespaced per user via userStorage utility
 * - Switching users automatically isolates their encrypted keys
 */

import { getUserItem, setUserItem, removeUserItem } from './userStorage';

const ALGORITHM = 'AES-GCM';

/**
 * Generate a simple hash of the encryption key for change detection.
 * Not cryptographically secure, just for detecting key changes.
 */
async function hashEncryptionKey(encryptionKey: string): Promise<string> {
    const encoder = new TextEncoder();
    const data = encoder.encode(encryptionKey);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.slice(0, 8).map(b => b.toString(16).padStart(2, '0')).join('');
}

/**
 * Check if encryption key has changed and clear stale data if so.
 * Call this before any key operations when you have the encryption key.
 */
export async function validateEncryptionKey(encryptionKey: string): Promise<boolean> {
    const currentHash = await hashEncryptionKey(encryptionKey);
    const storedHash = getUserItem('botchat_encryption_key_hash');
    
    if (storedHash && storedHash !== currentHash) {
        // Encryption key changed! Clear stale encrypted keys.
        console.warn('[BYOK] Encryption key changed - clearing stale localStorage keys');
        removeUserItem('botchat_encrypted_keys');
        setUserItem('botchat_encryption_key_hash', currentHash);
        return false; // Keys were cleared
    }
    
    // Store/update hash for future checks
    setUserItem('botchat_encryption_key_hash', currentHash);
    return true; // Keys are valid (or no keys stored)
}

/**
 * Derive a CryptoKey from the server-provided encryption key.
 */
async function deriveKey(encryptionKey: string): Promise<CryptoKey> {
    const encoder = new TextEncoder();
    const keyMaterial = await crypto.subtle.importKey(
        'raw',
        encoder.encode(encryptionKey),
        'PBKDF2',
        false,
        ['deriveKey']
    );
    
    // Use a fixed salt (the encryption key is already random/unique per user)
    const salt = encoder.encode('botchat-key-encryption-v1');
    
    return crypto.subtle.deriveKey(
        {
            name: 'PBKDF2',
            salt,
            iterations: 100000,
            hash: 'SHA-256'
        },
        keyMaterial,
        { name: ALGORITHM, length: 256 },
        false,
        ['encrypt', 'decrypt']
    );
}

/**
 * Encrypt a string value.
 */
async function encrypt(plaintext: string, encryptionKey: string): Promise<string> {
    const key = await deriveKey(encryptionKey);
    const encoder = new TextEncoder();
    const iv = crypto.getRandomValues(new Uint8Array(12));
    
    const ciphertext = await crypto.subtle.encrypt(
        { name: ALGORITHM, iv },
        key,
        encoder.encode(plaintext)
    );
    
    // Combine IV + ciphertext and encode as base64
    const combined = new Uint8Array(iv.length + ciphertext.byteLength);
    combined.set(iv);
    combined.set(new Uint8Array(ciphertext), iv.length);
    
    return btoa(String.fromCharCode(...combined));
}

/**
 * Decrypt a string value.
 */
async function decrypt(encryptedData: string, encryptionKey: string): Promise<string> {
    const key = await deriveKey(encryptionKey);
    const decoder = new TextDecoder();
    
    // Decode base64 and split IV + ciphertext
    const combined = Uint8Array.from(atob(encryptedData), c => c.charCodeAt(0));
    const iv = combined.slice(0, 12);
    const ciphertext = combined.slice(12);
    
    const plaintext = await crypto.subtle.decrypt(
        { name: ALGORITHM, iv },
        key,
        ciphertext
    );
    
    return decoder.decode(plaintext);
}

/**
 * Storage format for encrypted keys in localStorage.
 */
interface EncryptedKeyStore {
    version: number;
    keys: {
        [providerId: string]: {
            encrypted: string;  // Base64 encoded IV + ciphertext
            masked: string;     // First 8 chars for display
        };
    };
}

/**
 * Get the encrypted key store from localStorage.
 */
function getKeyStore(): EncryptedKeyStore {
    try {
        const stored = getUserItem('botchat_encrypted_keys');
        if (stored) {
            return JSON.parse(stored);
        }
    } catch {
        // Corrupted data, start fresh
    }
    return { version: 1, keys: {} };
}

/**
 * Save the encrypted key store to localStorage.
 */
function saveKeyStore(store: EncryptedKeyStore): void {
    setUserItem('botchat_encrypted_keys', JSON.stringify(store));
}

/**
 * Save an API key for a provider (encrypted).
 */
export async function saveProviderKey(
    providerId: string, 
    apiKey: string, 
    encryptionKey: string
): Promise<{ masked: string }> {
    const encrypted = await encrypt(apiKey, encryptionKey);
    const masked = apiKey.slice(0, 8) + '...';
    
    const store = getKeyStore();
    store.keys[providerId] = { encrypted, masked };
    saveKeyStore(store);
    
    return { masked };
}

/**
 * Get a decrypted API key for a provider.
 */
export async function getProviderKey(
    providerId: string, 
    encryptionKey: string
): Promise<string | null> {
    const store = getKeyStore();
    const entry = store.keys[providerId];
    
    if (!entry) {
        console.log(`[BYOK] No stored key entry for ${providerId}`);
        return null;
    }
    
    try {
        const decrypted = await decrypt(entry.encrypted, encryptionKey);
        console.log(`[BYOK] Successfully decrypted key for ${providerId}`);
        return decrypted;
    } catch (e) {
        // Decryption failed (wrong key or corrupted data)
        console.error(`[BYOK] Failed to decrypt key for ${providerId}:`, e);
        return null;
    }
}

/**
 * Delete a provider's API key.
 */
export function deleteProviderKey(providerId: string): void {
    const store = getKeyStore();
    delete store.keys[providerId];
    saveKeyStore(store);
}

/**
 * Get all configured providers (without decrypting keys).
 */
export function getConfiguredProviders(): { providerId: string; masked: string }[] {
    const store = getKeyStore();
    return Object.entries(store.keys).map(([providerId, entry]) => ({
        providerId,
        masked: entry.masked
    }));
}

/**
 * Check if a provider has a stored key.
 */
export function hasProviderKey(providerId: string): boolean {
    const store = getKeyStore();
    return providerId in store.keys;
}

/**
 * Clear all stored keys (e.g., on sign out).
 */
export function clearAllKeys(): void {
    removeUserItem('botchat_encrypted_keys');
    removeUserItem('botchat_encryption_key_hash');
}

/**
 * Get masked key display for a provider.
 */
export function getMaskedKey(providerId: string): string | null {
    const store = getKeyStore();
    return store.keys[providerId]?.masked ?? null;
}
