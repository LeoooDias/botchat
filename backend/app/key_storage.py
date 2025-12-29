"""
Secure API key storage for botchat.

Keys are encrypted using Fernet (AES-128-CBC) with a key derived from the
application's API_KEY using PBKDF2. This ensures:
1. Keys are never stored in plaintext
2. Keys persist across restarts (via mounted volume in Docker)
3. Keys are tied to this specific installation
"""

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Storage location - use Docker volume path or local data directory
# Docker: /data/keys
# Local: ~/.botchat/keys
def _get_storage_dir() -> Path:
    env_dir = os.environ.get("KEY_STORAGE_DIR")
    if env_dir:
        return Path(env_dir)
    # Default to user's home directory for local development
    return Path.home() / ".botchat" / "keys"

STORAGE_DIR = _get_storage_dir()
STORAGE_FILE = STORAGE_DIR / "provider_keys.enc"
SALT_FILE = STORAGE_DIR / "salt"

# Supported providers and their validation endpoints
SUPPORTED_PROVIDERS = {
    "openai": {
        "env_var": "OPENAI_API_KEY",
        "display_name": "OpenAI",
        "key_prefix": "sk-",
        "docs_url": "https://platform.openai.com/api-keys"
    },
    "gemini": {
        "env_var": "GOOGLE_API_KEY",
        "display_name": "Google Gemini",
        "key_prefix": "AIza",
        "docs_url": "https://aistudio.google.com/apikey"
    },
    "anthropic": {
        "env_var": "ANTHROPIC_API_KEY",
        "display_name": "Anthropic",
        "key_prefix": "sk-ant-",
        "docs_url": "https://console.anthropic.com/account/keys"
    }
}


def _get_encryption_key(api_key: str) -> bytes:
    """Derive a Fernet encryption key from the API_KEY using PBKDF2."""
    # Ensure storage directory exists
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Get or create salt
    if SALT_FILE.exists():
        salt = SALT_FILE.read_bytes()
    else:
        salt = os.urandom(16)
        SALT_FILE.write_bytes(salt)
    
    # Derive key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,  # OWASP recommended minimum
    )
    key = base64.urlsafe_b64encode(kdf.derive(api_key.encode()))
    return key


def _get_fernet(api_key: str) -> Fernet:
    """Get a Fernet instance for encryption/decryption."""
    return Fernet(_get_encryption_key(api_key))


def load_keys(api_key: str) -> Dict[str, str]:
    """Load and decrypt stored provider keys.
    
    Args:
        api_key: The application API_KEY used for encryption
        
    Returns:
        Dict mapping provider names to API keys
    """
    if not STORAGE_FILE.exists():
        return {}
    
    try:
        fernet = _get_fernet(api_key)
        encrypted_data = STORAGE_FILE.read_bytes()
        decrypted_data = fernet.decrypt(encrypted_data)
        return json.loads(decrypted_data.decode())
    except (InvalidToken, json.JSONDecodeError):
        # Corrupted or wrong key - return empty
        return {}


def save_keys(api_key: str, keys: Dict[str, str]) -> None:
    """Encrypt and save provider keys.
    
    Args:
        api_key: The application API_KEY used for encryption
        keys: Dict mapping provider names to API keys
    """
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    fernet = _get_fernet(api_key)
    data = json.dumps(keys).encode()
    encrypted_data = fernet.encrypt(data)
    STORAGE_FILE.write_bytes(encrypted_data)


def save_key(api_key: str, provider: str, provider_key: str) -> None:
    """Save a single provider key.
    
    Args:
        api_key: The application API_KEY used for encryption
        provider: Provider name (openai, gemini)
        provider_key: The provider's API key
    """
    keys = load_keys(api_key)
    keys[provider.lower()] = provider_key
    save_keys(api_key, keys)


def delete_key(api_key: str, provider: str) -> bool:
    """Delete a provider key.
    
    Args:
        api_key: The application API_KEY used for encryption
        provider: Provider name to delete
        
    Returns:
        True if key was deleted, False if it didn't exist
    """
    keys = load_keys(api_key)
    if provider.lower() in keys:
        del keys[provider.lower()]
        save_keys(api_key, keys)
        return True
    return False


def get_key(api_key: str, provider: str) -> Optional[str]:
    """Get a single provider key.
    
    Args:
        api_key: The application API_KEY used for encryption
        provider: Provider name
        
    Returns:
        The provider key or None if not found
    """
    keys = load_keys(api_key)
    return keys.get(provider.lower())


def get_configured_providers(api_key: str) -> Dict[str, dict]:
    """Get list of configured providers with metadata (not keys).
    
    Args:
        api_key: The application API_KEY used for encryption
        
    Returns:
        Dict with provider info and whether a key is configured
    """
    stored_keys = load_keys(api_key)
    
    result = {}
    for provider, info in SUPPORTED_PROVIDERS.items():
        # Check environment variable as fallback
        env_key = os.environ.get(info["env_var"], "")
        stored_key = stored_keys.get(provider, "")
        
        has_key = bool(stored_key or env_key)
        key_source = "stored" if stored_key else ("env" if env_key else None)
        
        # Mask the key for display (show first 8 chars)
        display_key = None
        if stored_key:
            display_key = stored_key[:8] + "..." if len(stored_key) > 8 else "***"
        elif env_key:
            display_key = env_key[:8] + "..." if len(env_key) > 8 else "***"
        
        result[provider] = {
            "display_name": info["display_name"],
            "configured": has_key,
            "source": key_source,
            "masked_key": display_key,
            "docs_url": info["docs_url"],
            "key_prefix": info["key_prefix"]
        }
    
    return result


def get_provider_key_for_use(api_key: str, provider: str) -> Optional[str]:
    """Get a provider key for actual use (stored takes precedence over env).
    
    Args:
        api_key: The application API_KEY used for encryption
        provider: Provider name
        
    Returns:
        The provider key to use, or None if not configured
    """
    # Stored key takes precedence
    stored_key = get_key(api_key, provider)
    if stored_key:
        return stored_key
    
    # Fall back to environment variable
    provider_info = SUPPORTED_PROVIDERS.get(provider.lower())
    if provider_info:
        return os.environ.get(provider_info["env_var"]) or None
    
    return None
