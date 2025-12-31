"""
Anthropic (Claude) provider implementation for botchat.

Supports both platform usage and BYOK (Bring Your Own Key).

Privacy & Data Handling:
- Anthropic does NOT use API inputs/outputs for model training by default
- Data may be retained up to 30 days for trust & safety (abuse monitoring)
- Enterprise plans can negotiate shorter retention periods
- No special headers required (unlike OpenAI's ZDR)

Reference: https://www.anthropic.com/policies/privacy
"""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional

import anthropic  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# -----------------------------
# Configuration
# -----------------------------

# Platform API key (from environment/secrets)
PLATFORM_ANTHROPIC_KEY = os.environ.get("PLATFORM_ANTHROPIC_API_KEY", "")

# Supported models (as of Dec 2025)
SUPPORTED_MODELS = {
    # Claude 4 family (2025)
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    # Claude 3.5 family
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-latest",
    "claude-3-5-haiku-20241022",
    "claude-3-5-haiku-latest",
    # Claude 3 family
    "claude-3-opus-20240229",
    "claude-3-opus-latest",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
    # Convenience aliases
    "claude-sonnet-4",
    "claude-opus-4",
}

# Models that support vision (image inputs)
VISION_MODELS = {
    "claude-sonnet-4-20250514",
    "claude-opus-4-20250514",
    "claude-sonnet-4",
    "claude-opus-4",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-latest",
    "claude-3-5-haiku-20241022",
    "claude-3-5-haiku-latest",
    "claude-3-opus-20240229",
    "claude-3-opus-latest",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
}

# Max tokens limits by model (approximate)
DEFAULT_MAX_TOKENS = 4096


@dataclass
class AnthropicConfig:
    """Configuration for Anthropic requests."""
    model: str
    api_key: Optional[str] = None  # If provided, use BYOK; otherwise platform key
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = 1.0


class AnthropicProvider:
    """
    Anthropic provider supporting both platform and BYOK usage.
    
    Usage:
        # Platform (uses botchat's API key)
        provider = AnthropicProvider()
        
        # BYOK (user's own key)
        provider = AnthropicProvider(api_key="sk-ant-...")
        
        # Stream response
        for chunk in provider.stream("Hello!", model="claude-sonnet-4-20250514"):
            print(chunk, end="")
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Anthropic provider.
        
        Args:
            api_key: Optional user API key. If not provided, uses platform key.
        """
        self.api_key = api_key or PLATFORM_ANTHROPIC_KEY
        self.is_byok = api_key is not None
        
        if not self.api_key:
            raise AnthropicConfigError("No Anthropic API key available (neither BYOK nor platform)")
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        
        # Log which mode we're in
        if self.is_byok:
            key_prefix = api_key[:12] if api_key and len(api_key) > 12 else "***"
            logger.info("🔑 BYOK MODE: Using user-provided Anthropic API key (prefix: %s...)", key_prefix)
        else:
            logger.info("🏢 PLATFORM MODE: Using botchat's Anthropic API key")
    
    def stream(
        self,
        message: str,
        model: str,
        system_instruction: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        file_data: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 1.0,
    ) -> Generator[str, None, None]:
        """
        Stream a response from Anthropic.
        
        Args:
            message: User message
            model: Model name (e.g., "claude-sonnet-4-20250514")
            system_instruction: Optional system prompt
            max_tokens: Maximum output tokens
            file_data: Optional list of file attachments [{bytes, mime_type, name}]
            temperature: Sampling temperature (0.0-1.0)
            
        Yields:
            Text chunks as they arrive
        """
        # Validate model
        if model not in SUPPORTED_MODELS:
            logger.warning("Model '%s' not in supported list, attempting anyway", model)
        
        # Build messages
        messages = self._build_messages(message, model, file_data)
        
        # Build request parameters
        request_params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # Add system instruction if provided
        if system_instruction:
            request_params["system"] = system_instruction
        
        # Stream response
        try:
            with self.client.messages.stream(**request_params) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except anthropic.RateLimitError as e:
            logger.error("Anthropic rate limit error: %s", str(e))
            raise RateLimitError(f"Rate limited by Anthropic API: {str(e)}")
        except anthropic.AuthenticationError as e:
            logger.error("Anthropic auth error: %s", str(e))
            raise AuthenticationError(f"Invalid API key: {str(e)}")
        except anthropic.BadRequestError as e:
            error_msg = str(e)
            logger.error("Anthropic bad request: %s", error_msg)
            if "context" in error_msg.lower() or "too long" in error_msg.lower():
                raise ContextLengthError(f"Message too long for model: {error_msg}")
            raise AnthropicAPIError(f"Bad request: {error_msg}")
        except anthropic.NotFoundError as e:
            logger.error("Anthropic model not found: %s", str(e))
            raise ModelNotFoundError(f"Model '{model}' not available: {str(e)}")
        except Exception as e:
            error_msg = str(e)
            logger.error("Anthropic streaming error: %s", error_msg)
            raise AnthropicAPIError(f"Anthropic API error: {error_msg}")
    
    def _build_messages(
        self,
        message: str,
        model: str,
        file_data: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Build messages array for the API request."""
        # Build user message content
        content: Any = message  # Default to simple string
        
        # Handle file attachments (images for vision models)
        if file_data and model in VISION_MODELS:
            content_parts: List[Dict[str, Any]] = []
            
            for fd in file_data:
                file_bytes = fd.get("bytes")
                mime_type = fd.get("mime_type", "application/octet-stream")
                filename = fd.get("name", "file")
                
                if file_bytes and mime_type.startswith("image/"):
                    # Base64 encode image
                    b64_data = base64.standard_b64encode(file_bytes).decode("utf-8")
                    content_parts.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": b64_data,
                        }
                    })
                    logger.debug("Added image to request: %s (%s, %d bytes)", 
                               filename, mime_type, len(file_bytes))
            
            # Add text part
            content_parts.append({
                "type": "text",
                "text": message,
            })
            
            content = content_parts
        elif file_data and model not in VISION_MODELS:
            logger.warning("Model %s doesn't support vision, ignoring %d file(s)", 
                         model, len(file_data))
        
        return [{"role": "user", "content": content}]
    
    @staticmethod
    def get_privacy_info(is_byok: bool = False) -> Dict[str, Any]:
        """Get privacy metadata for Anthropic.
        
        Args:
            is_byok: Whether this is a BYOK (user key) or platform key scenario
            
        Returns:
            Privacy metadata dict
        """
        base_info: Dict[str, Any] = {
            "provider": "anthropic",
            "provider_name": "Anthropic (Claude)",
            "docs_url": "https://www.anthropic.com/policies/privacy",
            "training_opt_out": True,  # API data NOT used for training by default
        }
        
        if is_byok:
            return {
                **base_info,
                "backend": "byok",
                "data_retention": "Up to 30 days for trust & safety",
                "enterprise_grade": False,  # Unless user has enterprise plan
                "compliance": ["SOC 2 Type 2"],
                "privacy_summary": "BYOK - Data not used for training, retained up to 30 days for safety",
                "privacy_level": "high",
                "user_action_available": "Enterprise plans can negotiate shorter retention",
            }
        else:
            return {
                **base_info,
                "backend": "platform",
                "data_retention": "Up to 30 days for trust & safety",
                "enterprise_grade": False,
                "compliance": ["SOC 2 Type 2"],
                "privacy_summary": "Platform key - Data not used for training, retained up to 30 days",
                "privacy_level": "high",
                "transparency_note": "Anthropic has strong default privacy (no training on API data)",
            }


# -----------------------------
# Custom Exceptions
# -----------------------------

class AnthropicAPIError(Exception):
    """Base exception for Anthropic API errors."""
    pass


class RateLimitError(AnthropicAPIError):
    """Rate limit exceeded."""
    pass


class AuthenticationError(AnthropicAPIError):
    """Authentication or authorization failed."""
    pass


class ModelNotFoundError(AnthropicAPIError):
    """Requested model not available."""
    pass


class ContextLengthError(AnthropicAPIError):
    """Input too long for model's context window."""
    pass


class AnthropicConfigError(AnthropicAPIError):
    """Configuration error (e.g., missing API key)."""
    pass


# -----------------------------
# Convenience Functions
# -----------------------------

def stream_anthropic(
    message: str,
    model: str,
    api_key: Optional[str] = None,
    system_instruction: Optional[str] = None,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    file_data: Optional[List[Dict[str, Any]]] = None,
    temperature: float = 1.0,
) -> Generator[str, None, None]:
    """
    Stream an Anthropic response.
    
    Convenience function that creates a provider and streams.
    
    Args:
        message: User message
        model: Model name
        api_key: Optional user API key (uses platform key if not provided)
        system_instruction: Optional system prompt
        max_tokens: Maximum output tokens
        file_data: Optional file attachments
        temperature: Sampling temperature
        
    Yields:
        Text chunks
    """
    provider = AnthropicProvider(api_key=api_key)
    yield from provider.stream(
        message=message,
        model=model,
        system_instruction=system_instruction,
        max_tokens=max_tokens,
        file_data=file_data,
        temperature=temperature,
    )


def get_anthropic_privacy_info(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Get privacy info for Anthropic.
    
    Args:
        api_key: If provided, returns BYOK privacy info; otherwise platform
        
    Returns:
        Privacy metadata dict
    """
    return AnthropicProvider.get_privacy_info(is_byok=api_key is not None)
