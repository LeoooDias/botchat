"""
OpenAI provider implementation for botchat.

Supports both platform usage and BYOK (Bring Your Own Key).

Privacy & Data Handling:
- ZDR (Zero Data Retention) header is always sent via X-OpenAI-No-Store
- IMPORTANT: ZDR is only honored for orgs with formal enterprise agreements
- Platform usage: botchat does NOT have ZDR agreement (data retained up to 30 days)
- BYOK usage: ZDR honored only if user's org has ZDR agreement with OpenAI

Transparency is key - we communicate these limitations clearly to users.
"""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Generator, List, Optional

from openai import OpenAI, Stream  # type: ignore[import-untyped]
from openai.types.chat import ChatCompletionChunk  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

# -----------------------------
# Configuration
# -----------------------------

# Platform API key (from environment/secrets)
PLATFORM_OPENAI_KEY = os.environ.get("PLATFORM_OPENAI_API_KEY", "")

# Supported models (as of Dec 2025)
SUPPORTED_MODELS = {
    # GPT-4 family
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4",
    # GPT-4.1 family (2025)
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    # o1/o3 reasoning models
    "o1",
    "o1-mini",
    "o1-preview",
    "o3-mini",
    # Legacy
    "gpt-3.5-turbo",
}

# Models that support vision (image inputs)
VISION_MODELS = {
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-4.1",
    "gpt-4.1-mini",
    "o1",
}

# Models that DON'T support system instructions (reasoning models)
NO_SYSTEM_INSTRUCTION_MODELS = {
    "o1",
    "o1-mini",
    "o1-preview",
    "o3-mini",
}


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI requests."""
    model: str
    api_key: Optional[str] = None  # If provided, use BYOK; otherwise platform key
    max_tokens: int = 4000
    temperature: float = 1.0
    top_p: float = 1.0


class OpenAIProvider:
    """
    OpenAI provider supporting both platform and BYOK usage.
    
    Usage:
        # Platform (uses botchat's API key)
        provider = OpenAIProvider()
        
        # BYOK (user's own key)
        provider = OpenAIProvider(api_key="sk-...")
        
        # Stream response
        for chunk in provider.stream("Hello!", model="gpt-4o"):
            print(chunk, end="")
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: Optional user API key. If not provided, uses platform key.
        """
        self.api_key = api_key or PLATFORM_OPENAI_KEY
        self.is_byok = api_key is not None
        
        if not self.api_key:
            raise OpenAIConfigError("No OpenAI API key available (neither BYOK nor platform)")
        
        # Create client with ZDR header
        # NOTE: This header is only honored for orgs with formal ZDR agreements
        self.client = OpenAI(
            api_key=self.api_key,
            default_headers={
                "X-OpenAI-No-Store": "true",  # Request ZDR (not guaranteed)
            }
        )
        
        # Log which mode we're in
        if self.is_byok:
            key_prefix = api_key[:8] if api_key and len(api_key) > 8 else "***"
            logger.info("🔑 BYOK MODE: Using user-provided OpenAI API key (prefix: %s...)", key_prefix)
        else:
            logger.info("🏢 PLATFORM MODE: Using botchat's OpenAI API key")
    
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
        Stream a response from OpenAI.
        
        Args:
            message: User message
            model: Model name (e.g., "gpt-4o")
            system_instruction: Optional system prompt (ignored for o1/o3 models)
            max_tokens: Maximum output tokens
            file_data: Optional list of file attachments [{bytes, mime_type, name}]
            temperature: Sampling temperature (0.0-2.0)
            
        Yields:
            Text chunks as they arrive
        """
        # Validate model
        if model not in SUPPORTED_MODELS:
            logger.warning("Model '%s' not in supported list, attempting anyway", model)
        
        # Build messages
        messages = self._build_messages(message, model, system_instruction, file_data)
        
        # Build request parameters
        request_params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }
        
        # Add optional parameters (some models don't support all params)
        if model not in NO_SYSTEM_INSTRUCTION_MODELS:
            request_params["max_completion_tokens"] = max_tokens
            request_params["temperature"] = temperature
        else:
            # Reasoning models use max_completion_tokens but not temperature
            request_params["max_completion_tokens"] = max_tokens
        
        # Stream response
        try:
            response_stream: Stream[ChatCompletionChunk] = self.client.chat.completions.create(**request_params)  # type: ignore[assignment]
            
            for chunk in response_stream:  # pyright: ignore[reportUnknownVariableType]
                if chunk.choices and chunk.choices[0].delta.content:  # pyright: ignore[reportUnknownMemberType]
                    yield chunk.choices[0].delta.content  # pyright: ignore[reportUnknownMemberType]
                    
        except Exception as e:
            error_msg = str(e)
            logger.error("OpenAI streaming error: %s", error_msg)
            
            # Provide user-friendly error messages
            if "429" in error_msg or "rate" in error_msg.lower():
                raise RateLimitError(f"Rate limited by OpenAI API: {error_msg}")
            elif "401" in error_msg or "invalid_api_key" in error_msg.lower():
                raise AuthenticationError(f"Invalid API key: {error_msg}")
            elif "403" in error_msg or "permission" in error_msg.lower():
                raise AuthenticationError(f"Permission denied: {error_msg}")
            elif "model" in error_msg.lower() and ("not found" in error_msg.lower() or "does not exist" in error_msg.lower()):
                raise ModelNotFoundError(f"Model '{model}' not available: {error_msg}")
            elif "context_length" in error_msg.lower() or "maximum context" in error_msg.lower():
                raise ContextLengthError(f"Message too long for model: {error_msg}")
            else:
                raise OpenAIAPIError(f"OpenAI API error: {error_msg}")
    
    def _build_messages(
        self,
        message: str,
        model: str,
        system_instruction: Optional[str] = None,
        file_data: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Build messages array for the API request."""
        messages: List[Dict[str, Any]] = []
        
        # Add system message (if supported by model)
        if system_instruction and model not in NO_SYSTEM_INSTRUCTION_MODELS:
            messages.append({
                "role": "system",
                "content": system_instruction,
            })
        elif system_instruction and model in NO_SYSTEM_INSTRUCTION_MODELS:
            # For reasoning models, prepend system instruction to user message
            logger.debug("Model %s doesn't support system instructions, prepending to user message", model)
            message = f"[Instructions]\n{system_instruction}\n\n[User Message]\n{message}"
        
        # Build user message content
        user_content: Any = message  # Default to simple string
        
        # Handle file attachments (images only for vision models)
        if file_data and model in VISION_MODELS:
            # Multi-part content for vision
            content_parts: List[Dict[str, Any]] = []
            
            for fd in file_data:
                file_bytes = fd.get("bytes")
                mime_type = fd.get("mime_type", "application/octet-stream")
                filename = fd.get("name", "file")
                
                if file_bytes and mime_type.startswith("image/"):
                    # Base64 encode image
                    b64_data = base64.standard_b64encode(file_bytes).decode("utf-8")
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_data}",
                            "detail": "auto",  # Let OpenAI choose resolution
                        }
                    })
                    logger.debug("Added image to request: %s (%s, %d bytes)", 
                               filename, mime_type, len(file_bytes))
            
            # Add text part
            content_parts.append({
                "type": "text",
                "text": message,
            })
            
            user_content = content_parts
        elif file_data and model not in VISION_MODELS:
            logger.warning("Model %s doesn't support vision, ignoring %d file(s)", 
                         model, len(file_data))
        
        messages.append({
            "role": "user",
            "content": user_content,
        })
        
        return messages
    
    @staticmethod
    def get_privacy_info(is_byok: bool = False) -> Dict[str, Any]:
        """Get privacy metadata for OpenAI.
        
        Args:
            is_byok: Whether this is a BYOK (user key) or platform key scenario
            
        Returns:
            Privacy metadata dict with accurate ZDR information
        """
        base_info: Dict[str, Any] = {
            "provider": "openai",
            "provider_name": "OpenAI",
            "docs_url": "https://openai.com/policies/api-data-usage-policies",
            "zdr_header_sent": True,  # We always send X-OpenAI-No-Store
        }
        
        if is_byok:
            return {
                **base_info,
                "backend": "byok",
                "data_retention": "Up to 30 days (ZDR honored only with enterprise agreement)",
                "training_opt_out": True,  # API data not used for training by default
                "zdr_honored": "Only if your organization has a ZDR agreement with OpenAI",
                "enterprise_grade": False,  # Unless user has enterprise plan
                "compliance": ["SOC 2 Type 2"],
                "privacy_summary": "BYOK - ZDR header sent, honored only with enterprise ZDR agreement",
                "privacy_level": "medium",
                "user_action_available": "Contact OpenAI for enterprise ZDR agreement",
            }
        else:
            return {
                **base_info,
                "backend": "platform",
                "data_retention": "Up to 30 days for abuse monitoring",
                "training_opt_out": True,  # API data not used for training
                "zdr_honored": False,  # botchat doesn't have ZDR agreement
                "enterprise_grade": False,
                "compliance": ["SOC 2 Type 2"],
                "privacy_summary": "Platform key - Data retained up to 30 days (no ZDR agreement)",
                "privacy_level": "medium",
                "transparency_note": "botchat has not applied for OpenAI's ZDR program",
            }


# -----------------------------
# Custom Exceptions
# -----------------------------

class OpenAIAPIError(Exception):
    """Base exception for OpenAI API errors."""
    pass


class RateLimitError(OpenAIAPIError):
    """Rate limit exceeded."""
    pass


class AuthenticationError(OpenAIAPIError):
    """Authentication or authorization failed."""
    pass


class ModelNotFoundError(OpenAIAPIError):
    """Requested model not available."""
    pass


class ContextLengthError(OpenAIAPIError):
    """Input too long for model's context window."""
    pass


class OpenAIConfigError(OpenAIAPIError):
    """Configuration error (e.g., missing API key)."""
    pass


# -----------------------------
# Convenience Functions
# -----------------------------

def stream_openai(
    message: str,
    model: str,
    api_key: Optional[str] = None,
    system_instruction: Optional[str] = None,
    max_tokens: int = 4000,
    file_data: Optional[List[Dict[str, Any]]] = None,
    temperature: float = 1.0,
) -> Generator[str, None, None]:
    """
    Stream an OpenAI response.
    
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
    provider = OpenAIProvider(api_key=api_key)
    yield from provider.stream(
        message=message,
        model=model,
        system_instruction=system_instruction,
        max_tokens=max_tokens,
        file_data=file_data,
        temperature=temperature,
    )


def get_openai_privacy_info(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Get privacy info for OpenAI.
    
    Args:
        api_key: If provided, returns BYOK privacy info; otherwise platform
        
    Returns:
        Privacy metadata dict
    """
    return OpenAIProvider.get_privacy_info(is_byok=api_key is not None)
