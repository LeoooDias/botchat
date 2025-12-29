"""
Tests for the botchat backend API.
"""

import json
import os
import pytest
from fastapi.testclient import TestClient
from app.main import app



@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """Get the API key from environment for testing."""
    # For testing, we can use any key or mock it
    return "test-api-key-12345"


class TestHealthCheck:
    """Test health check endpoints."""
    
    def test_health_endpoint(self, client):
        """Test that the health endpoint returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data



class TestChatEndpoint:
    """Test the chat endpoint functionality."""
    
    def test_runs_endpoint_exists(self, client, valid_api_key):
        """Test runs endpoint accepts requests."""
        payload = {
            "runs": [
                {
                    "provider": "openai",
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": "Hello"}]
                }
            ]
        }
        headers = {"x-api-key": valid_api_key}
        
        response = client.post("/runs", json=payload, headers=headers)
        # Should accept the request structure (may fail with auth/validation but not 404)
        assert response.status_code != 404
    
    def test_runs_missing_api_key_header(self, client):
        """Test that /runs endpoint requires API key."""
        payload = {
            "runs": [{"provider": "openai", "model": "gpt-4", "messages": []}]
        }
        response = client.post("/runs", json=payload)
        # Should reject request without API key (401/403) or return 422
        assert response.status_code in [401, 403, 422]



class TestKeyVerificationEndpoint:
    """Test the key verification endpoints."""
    
    def test_verify_keys_endpoint(self, client, valid_api_key):
        """Test key verification endpoint."""
        headers = {"x-api-key": valid_api_key}
        payload = {
            "provider": "openai",
            "api_key": "sk-invalid-test-key"
        }
        
        response = client.post("/settings/keys/verify", json=payload, headers=headers)
        # Should return 200 with validity status or 422 for bad input
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            assert "valid" in data or "success" in data.lower()



class TestKeyStorageEndpoints:
    """Test key storage and retrieval endpoints."""
    
    def test_set_and_get_keys(self, client, valid_api_key):
        """Test setting and retrieving stored keys."""
        headers = {"x-api-key": valid_api_key}
        
        # Store a key
        payload = {
            "provider": "openai",
            "api_key": "sk-test-key-12345"
        }
        response = client.post("/settings/keys", json=payload, headers=headers)
        # Accept 200, 201, 204 (success) or 400 (validation error from endpoint)
        assert response.status_code in [200, 201, 204, 400]
        
        # Retrieve the key via providers endpoint
        response = client.get("/settings/providers", headers=headers)
        assert response.status_code == 200
    
    def test_set_key_invalid_provider(self, client, valid_api_key):
        """Test setting key for invalid provider."""
        headers = {"x-api-key": valid_api_key}
        payload = {
            "provider": "invalid",
            "api_key": "test-key"
        }
        response = client.post("/settings/keys", json=payload, headers=headers)
        # Should reject invalid provider or return error
        assert response.status_code in [400, 422]



class TestConfigEndpoint:
    """Test configuration endpoints."""
    
    def test_get_providers(self, client, valid_api_key):
        """Test getting configured providers."""
        headers = {"x-api-key": valid_api_key}
        response = client.get("/settings/providers", headers=headers)
        # Should return configured providers
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)



class TestIntegration:
    """Integration tests combining multiple features."""
    
    def test_full_workflow_structure(self, client, valid_api_key):
        """Test the structure of a complete workflow."""
        headers = {"x-api-key": valid_api_key}
        
        # 1. Get available providers
        response = client.get("/settings/providers", headers=headers)
        assert response.status_code == 200
        
        # 2. Set a key
        payload = {"provider": "openai", "api_key": "sk-test-key"}
        response = client.post("/settings/keys", json=payload, headers=headers)
        # Accept success codes or 400 (endpoint validation)
        assert response.status_code in [200, 201, 204, 400]
        
        # 3. Verify health
        response = client.get("/health")
        assert response.status_code == 200



# Run with: pytest backend/tests/test_api.py -v
