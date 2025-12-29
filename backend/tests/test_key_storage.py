"""
Tests for key storage and encryption functionality.
"""

import pytest
from app.key_storage import save_key, get_key, load_keys, save_keys
import os
import tempfile


@pytest.fixture
def test_api_key():
    """Get the test API key."""
    return "test-api-key-12345"


@pytest.fixture
def temp_keys_dir(monkeypatch):
    """Create a temporary directory for testing key storage."""
    with tempfile.TemporaryDirectory() as temp_dir:
        monkeypatch.setenv("KEY_STORAGE_DIR", temp_dir)
        yield temp_dir


class TestKeyStorage:
    """Test the key storage functions."""
    
    def test_save_and_retrieve_key(self, test_api_key, temp_keys_dir):
        """Test saving and retrieving an API key."""
        provider = "openai"
        test_key = "sk-test-openai-key-12345"
        
        # Save a key
        save_key(test_api_key, provider, test_key)
        
        # Retrieve the key
        retrieved = get_key(test_api_key, provider)
        assert retrieved == test_key
    
    def test_save_multiple_providers(self, test_api_key, temp_keys_dir):
        """Test saving keys for multiple providers."""
        openai_key = "sk-openai-test"
        gemini_key = "gemini-test-key"
        
        save_key(test_api_key, "openai", openai_key)
        save_key(test_api_key, "gemini", gemini_key)
        
        assert get_key(test_api_key, "openai") == openai_key
        assert get_key(test_api_key, "gemini") == gemini_key
    
    def test_retrieve_nonexistent_key(self, test_api_key, temp_keys_dir):
        """Test retrieving a key that doesn't exist."""
        retrieved = get_key(test_api_key, "nonexistent")
        assert retrieved is None
    
    def test_update_existing_key(self, test_api_key, temp_keys_dir):
        """Test updating an existing key."""
        provider = "openai"
        old_key = "sk-old-key"
        new_key = "sk-new-key"
        
        save_key(test_api_key, provider, old_key)
        save_key(test_api_key, provider, new_key)
        
        assert get_key(test_api_key, provider) == new_key
    
    def test_load_all_keys(self, test_api_key, temp_keys_dir):
        """Test loading all stored keys."""
        save_key(test_api_key, "openai", "sk-test-1")
        save_key(test_api_key, "gemini", "gemini-test-1")
        
        keys = load_keys(test_api_key)
        
        assert "openai" in keys
        assert "gemini" in keys
        assert keys["openai"] == "sk-test-1"
        assert keys["gemini"] == "gemini-test-1"
    
    def test_save_and_load_keys_dict(self, test_api_key, temp_keys_dir):
        """Test saving and loading a dictionary of keys."""
        keys_dict = {
            "openai": "sk-test-key",
            "gemini": "gemini-test-key"
        }
        
        save_keys(test_api_key, keys_dict)
        loaded = load_keys(test_api_key)
        
        assert loaded == keys_dict


# Run with: pytest backend/tests/test_key_storage.py -v

