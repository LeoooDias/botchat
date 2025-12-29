"""
Pytest configuration and fixtures for botchat backend tests.
"""

import os
import pytest


# Set test API_KEY before app import
os.environ["API_KEY"] = "test-api-key-12345"
os.environ["REQUIRE_API_KEY"] = "true"


@pytest.fixture
def valid_api_key():
    """Get the API key for testing."""
    return "test-api-key-12345"
