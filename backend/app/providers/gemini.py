"""
Gemini provider implementation for botchat.

Supports two backends:
1. Vertex AI (platform usage) - GCP service account authentication
2. AI Studio (BYOK) - User-provided API keys

Both use Google's unified SDK (google-genai) for consistent behavior.

Privacy & Data Handling:
- Vertex AI: Enterprise-grade, data processed in specified region
- AI Studio: Consumer API, may be used for model improvements (free tier)
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional

from google import genai  # type: ignore[import-untyped]
from google.genai import types  # type: ignore[import-untyped]
from google.oauth2 import service_account  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# -----------------------------
# Configuration
# -----------------------------

# GCP project and region for Vertex AI
VERTEX_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "botchat-prod-1228")
VERTEX_REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

# Service account credentials (JSON string from Secret Manager)
VERTEX_SERVICE_ACCOUNT_JSON = os.environ.get("VERTEX_AI_SERVICE_ACCOUNT", "")

# Supported models (as of Dec 2025)
SUPPORTED_MODELS = {
    "gemini-3-pro-preview",
    "gemini-3-flash-preview",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    # Legacy models (for backward compatibility)
    "gemini-2.0-flash-exp",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
}


@dataclass
class GeminiConfig:
    """Configuration for Gemini requests."""
    model: str
    api_key: Optional[str] = None  # If provided, use AI Studio; otherwise Vertex AI
    max_tokens: int = 4000
    temperature: float = 1.0
    top_p: float = 0.95
    top_k: int = 40


class GeminiProvider:
    """
    Unified Gemini provider supporting both Vertex AI and AI Studio backends.
    
    Usage:
        # Platform (Vertex AI)
        provider = GeminiProvider()
        
        # BYOK (AI Studio)
        provider = GeminiProvider(api_key="AIza...")
        
        # Stream response
        for chunk in provider.stream("Hello!", model="gemini-2.5-flash"):
            print(chunk, end="")
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Optional AI Studio API key. If not provided, uses Vertex AI
                    with service account credentials.
        """
        self.api_key = api_key
        self.client = self._create_client()
        self.backend = "ai_studio" if api_key else "vertex_ai"
        
        # Log which backend is being used (helpful for debugging BYOK vs Platform)
        if api_key:
            logger.info("🔑 BYOK MODE: Using AI Studio with user-provided API key (key prefix: %s...)", api_key[:8] if len(api_key) > 8 else "***")
        else:
            logger.info("🏢 PLATFORM MODE: Using Vertex AI with service account")
        
    def _create_client(self) -> genai.Client:
        """Create the appropriate genai client based on auth method."""
        if self.api_key:
            # AI Studio: Use API key
            logger.debug("Creating AI Studio client with API key")
            return genai.Client(api_key=self.api_key)
        else:
            # Vertex AI: Use service account credentials
            logger.debug("Creating Vertex AI client for project=%s, region=%s", 
                        VERTEX_PROJECT, VERTEX_REGION)
            
            if VERTEX_SERVICE_ACCOUNT_JSON:
                # Parse service account JSON from environment
                try:
                    sa_info = json.loads(VERTEX_SERVICE_ACCOUNT_JSON)
                    credentials = service_account.Credentials.from_service_account_info(  # type: ignore[no-untyped-call]
                        sa_info,
                        scopes=["https://www.googleapis.com/auth/cloud-platform"]
                    )
                    return genai.Client(
                        vertexai=True,
                        project=VERTEX_PROJECT,
                        location=VERTEX_REGION,
                        credentials=credentials,
                    )
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse VERTEX_AI_SERVICE_ACCOUNT JSON: %s", e)
                    raise RuntimeError("Invalid Vertex AI service account configuration")
            else:
                # Fall back to Application Default Credentials (ADC)
                # Works in Cloud Run with attached service account
                logger.debug("Using Application Default Credentials for Vertex AI")
                return genai.Client(
                    vertexai=True,
                    project=VERTEX_PROJECT,
                    location=VERTEX_REGION,
                )
    
    def stream(
        self,
        message: str,
        model: str,
        system_instruction: Optional[str] = None,
        max_tokens: int = 4000,
        file_data: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 1.0,
    ) -> Generator[str, None, None]:
        """
        Stream a response from Gemini.
        
        Args:
            message: User message
            model: Model name (e.g., "gemini-2.5-flash")
            system_instruction: Optional system prompt
            max_tokens: Maximum output tokens
            file_data: Optional list of file attachments [{bytes, mime_type, name}]
            temperature: Sampling temperature (0.0-2.0)
            
        Yields:
            Text chunks as they arrive
        """
        # Validate model
        if model not in SUPPORTED_MODELS:
            logger.warning("Model '%s' not in supported list, attempting anyway", model)
        
        # Build content parts
        contents = self._build_contents(message, file_data)
        
        # Build generation config
        config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            top_p=0.95,
            top_k=40,
        )
        
        if system_instruction:
            config.system_instruction = system_instruction
        
        # Stream response
        try:
            response_stream = self.client.models.generate_content_stream(  # type: ignore[misc]
                model=model,
                contents=contents,
                config=config,
            )
            
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            error_msg = str(e)
            logger.error("Gemini streaming error (%s): %s", self.backend, error_msg)
            
            # Provide user-friendly error messages
            if "429" in error_msg or "quota" in error_msg.lower():
                raise RateLimitError(f"Rate limited by Gemini API: {error_msg}")
            elif "401" in error_msg or "403" in error_msg or "permission" in error_msg.lower():
                raise AuthenticationError(f"Authentication failed: {error_msg}")
            elif "invalid" in error_msg.lower() and "model" in error_msg.lower():
                raise ModelNotFoundError(f"Model '{model}' not available: {error_msg}")
            else:
                raise GeminiAPIError(f"Gemini API error: {error_msg}")
    
    def _build_contents(
        self, 
        message: str, 
        file_data: Optional[List[Dict[str, Any]]] = None
    ) -> List[types.Content]:
        """Build content parts for the API request."""
        parts: List[Any] = []
        
        # Add file attachments first (if any)
        if file_data:
            for fd in file_data:
                file_bytes = fd.get("bytes")
                mime_type = fd.get("mime_type", "application/octet-stream")
                
                if file_bytes:
                    # Inline data (base64 encoded by SDK)
                    parts.append(types.Part.from_bytes(
                        data=file_bytes,
                        mime_type=mime_type,
                    ))
        
        # Add text message
        parts.append(types.Part.from_text(text=message))
        
        return [types.Content(role="user", parts=parts)]
    
    @staticmethod
    def get_privacy_info() -> Dict[str, Any]:
        """Get privacy metadata for Gemini.
        
        Returns different info based on backend (Vertex AI vs AI Studio).
        """
        # Base privacy info (common to both)
        base_info = {
            "provider": "gemini",
            "provider_name": "Google Gemini",
            "docs_url": "https://cloud.google.com/vertex-ai/generative-ai/docs/data-governance",
        }
        
        # Vertex AI privacy (platform usage)
        vertex_info: Dict[str, Any] = {
            **base_info,
            "backend": "vertex_ai",
            "data_retention": "Request data not used for model training",
            "data_location": f"Processed in {VERTEX_REGION}",
            "training_opt_out": True,
            "enterprise_grade": True,
            "compliance": ["SOC 2", "ISO 27001", "HIPAA eligible"],
            "privacy_summary": "Enterprise Vertex AI - Data not used for training, processed in specified region",
            "privacy_level": "high",
        }
        
        # AI Studio privacy (BYOK usage)
        aistudio_info: Dict[str, Any] = {
            **base_info,
            "backend": "ai_studio",
            "data_retention": "May be retained for abuse monitoring (paid tier: ~24-72h)",
            "data_location": "Google Cloud (region may vary)",
            "training_opt_out": "Paid tier only",
            "enterprise_grade": False,
            "compliance": ["SOC 2"],
            "privacy_summary": "AI Studio API - Paid tier data not used for training, free tier may be used",
            "privacy_level": "medium",
            "free_tier_warning": "Free tier usage may be used for model improvements",
        }
        
        return {
            "vertex_ai": vertex_info,
            "ai_studio": aistudio_info,
        }


# -----------------------------
# Custom Exceptions
# -----------------------------

class GeminiAPIError(Exception):
    """Base exception for Gemini API errors."""
    pass


class RateLimitError(GeminiAPIError):
    """Rate limit exceeded."""
    pass


class AuthenticationError(GeminiAPIError):
    """Authentication or authorization failed."""
    pass


class ModelNotFoundError(GeminiAPIError):
    """Requested model not available."""
    pass


# -----------------------------
# Convenience Functions
# -----------------------------

def stream_gemini(
    message: str,
    model: str,
    api_key: Optional[str] = None,
    system_instruction: Optional[str] = None,
    max_tokens: int = 4000,
    file_data: Optional[List[Dict[str, Any]]] = None,
) -> Generator[str, None, None]:
    """
    Stream a Gemini response.
    
    Convenience function that creates a provider and streams.
    
    Args:
        message: User message
        model: Model name
        api_key: Optional AI Studio API key (uses Vertex AI if not provided)
        system_instruction: Optional system prompt
        max_tokens: Maximum output tokens
        file_data: Optional file attachments
        
    Yields:
        Text chunks
    """
    provider = GeminiProvider(api_key=api_key)
    yield from provider.stream(
        message=message,
        model=model,
        system_instruction=system_instruction,
        max_tokens=max_tokens,
        file_data=file_data,
    )


def get_gemini_privacy_info(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Get privacy info for the appropriate Gemini backend.
    
    Args:
        api_key: If provided, returns AI Studio privacy info; otherwise Vertex AI
        
    Returns:
        Privacy metadata dict
    """
    all_info = GeminiProvider.get_privacy_info()
    
    if api_key:
        return all_info["ai_studio"]
    else:
        return all_info["vertex_ai"]
