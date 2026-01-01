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
import io
import logging
import os
from dataclasses import dataclass, field
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


def _strip_exif_metadata(image_bytes: bytes, mime_type: str) -> bytes:
    """
    Strip EXIF metadata from images for privacy.
    
    EXIF data can contain sensitive info: GPS coordinates, device identifiers,
    timestamps, camera settings, etc. We strip it before sending to Anthropic.
    
    Args:
        image_bytes: Raw image bytes
        mime_type: Image MIME type (e.g., "image/jpeg")
        
    Returns:
        Image bytes with EXIF stripped (or original if stripping fails)
    """
    try:
        from PIL import Image
        
        # Only process supported formats
        if mime_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
            return image_bytes
        
        # Load image
        img = Image.open(io.BytesIO(image_bytes))
        
        # Create clean copy without EXIF
        output = io.BytesIO()
        
        if mime_type == "image/jpeg":
            img_rgb = img.convert("RGB") if img.mode != "RGB" else img
            img_rgb.save(output, format="JPEG", quality=95)
        elif mime_type == "image/png":
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(list(img.getdata()))
            clean_img.save(output, format="PNG")
        elif mime_type == "image/webp":
            img.save(output, format="WEBP", quality=95)
        elif mime_type == "image/gif":
            img.save(output, format="GIF")
        else:
            return image_bytes
        
        stripped_bytes = output.getvalue()
        logger.debug("Stripped EXIF metadata: %d -> %d bytes", len(image_bytes), len(stripped_bytes))
        return stripped_bytes
        
    except ImportError:
        logger.warning("Pillow not installed - cannot strip EXIF metadata from images")
        return image_bytes
    except Exception as e:
        logger.warning("Failed to strip EXIF metadata: %s", type(e).__name__)
        return image_bytes


@dataclass
class AnthropicConfig:
    """Configuration for Anthropic requests."""
    model: str
    api_key: Optional[str] = None  # If provided, use BYOK; otherwise platform key
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = 1.0
    strip_metadata: bool = True  # Privacy: don't log filenames by default
    enable_prompt_caching: bool = False  # Privacy: explicit opt-in for prompt caching


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
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        additional_headers: Optional[Dict[str, str]] = None,
        strip_metadata: bool = True,
    ):
        """
        Initialize Anthropic provider.
        
        Args:
            api_key: Optional user API key. If not provided, uses platform key.
            additional_headers: Optional dict of additional HTTP headers to send.
            strip_metadata: If True, don't log filenames/sensitive metadata (default: True).
        """
        self.api_key = api_key or PLATFORM_ANTHROPIC_KEY
        self.is_byok = api_key is not None
        self.strip_metadata = strip_metadata
        
        if not self.api_key:
            raise AnthropicConfigError("No Anthropic API key available (neither BYOK nor platform)")
        
        # Create client with optional additional headers
        client_kwargs: Dict[str, Any] = {"api_key": self.api_key}
        if additional_headers:
            client_kwargs["default_headers"] = additional_headers
        
        self.client = anthropic.Anthropic(**client_kwargs)
        
        # Log which mode we're in (no key material - even prefixes are risky in logs)
        if self.is_byok:
            logger.info("🔑 BYOK MODE: Using user-provided Anthropic API key")
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
        user_id: Optional[str] = None,
        enable_prompt_caching: bool = False,
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
            user_id: Optional hashed user ID for privacy-preserving abuse monitoring.
                    Should be a hash/UUID, NOT raw PII like email addresses.
            enable_prompt_caching: If True, enable ephemeral prompt caching for system
                                  instructions (explicit opt-in for privacy).
            
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
        
        # Add hashed user ID for privacy-preserving abuse monitoring
        # This helps Anthropic with rate limiting and abuse detection without storing PII
        if user_id:
            request_params["metadata"] = {"user_id": user_id}
        
        # Add system instruction (with optional prompt caching)
        if system_instruction:
            if enable_prompt_caching:
                # Use caching format - cache_control: ephemeral means it can be cached
                # but will be automatically evicted (not persisted long-term)
                request_params["system"] = [
                    {
                        "type": "text",
                        "text": system_instruction,
                        "cache_control": {"type": "ephemeral"}
                    }
                ]
                logger.debug("Using ephemeral prompt caching for system instruction")
            else:
                request_params["system"] = system_instruction
        
        # Stream response
        try:
            with self.client.messages.stream(**request_params) as stream:
                for text in stream.text_stream:
                    yield text
                    
        except anthropic.RateLimitError as e:
            logger.error("Anthropic rate limit error (%s)", type(e).__name__)
            logger.debug("Anthropic rate limit detail: %r", e)
            raise RateLimitError("Rate limited by Anthropic API. Please try again later.")
        except anthropic.AuthenticationError as e:
            logger.error("Anthropic auth error (%s)", type(e).__name__)
            logger.debug("Anthropic auth error detail: %r", e)
            raise AuthenticationError("Invalid API key. Please check your Anthropic API key.")
        except anthropic.BadRequestError as e:
            error_msg = str(e)
            error_lower = error_msg.lower()
            logger.error("Anthropic bad request (%s)", type(e).__name__)
            logger.debug("Anthropic bad request detail: %r", e)
            if "context" in error_lower or "too long" in error_lower:
                raise ContextLengthError("Message too long for this model's context window.")
            raise AnthropicAPIError("Bad request to Anthropic API. Please check your input.")
        except anthropic.NotFoundError as e:
            logger.error("Anthropic model not found (%s)", type(e).__name__)
            logger.debug("Anthropic not found detail: %r", e)
            raise ModelNotFoundError(f"Model '{model}' is not available.")
        except Exception as e:
            # Tightened logging: avoid leaking prompts via exception strings
            logger.error("Anthropic streaming error (%s)", type(e).__name__)
            logger.debug("Anthropic streaming error detail: %r", e)
            raise AnthropicAPIError("Anthropic API error. Please try again.")
    
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
                    # Strip EXIF metadata for privacy (GPS, device IDs, timestamps, etc.)
                    clean_bytes = _strip_exif_metadata(file_bytes, mime_type)
                    
                    # Base64 encode image
                    b64_data = base64.standard_b64encode(clean_bytes).decode("utf-8")
                    content_parts.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": b64_data,
                        }
                    })
                    
                    # Conditional logging based on privacy settings
                    if not self.strip_metadata:
                        logger.debug("Added image: %s (%s, %d bytes, EXIF stripped)", 
                                   filename, mime_type, len(clean_bytes))
                    else:
                        logger.debug("Added image (%s, %d bytes, EXIF stripped)", 
                                   mime_type, len(clean_bytes))
            
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
            Privacy metadata dict with actionable information
        """
        base_info: Dict[str, Any] = {
            "provider": "anthropic",
            "provider_name": "Anthropic (Claude)",
            "docs_url": "https://www.anthropic.com/policies/privacy",
            "training_opt_out": True,  # API data NOT used for training by default
            "data_usage": {
                "training": False,
                "trust_and_safety": True,
                "retention_days": 30,
            },
            "privacy_features": {
                "user_id_support": True,  # Hashed user IDs for abuse monitoring
                "prompt_caching": "opt-in",  # Ephemeral caching available
                "exif_stripping": True,  # We strip EXIF from images
            },
            "recommendations": [
                "Use hashed user IDs (not raw PII) for abuse monitoring",
                "Consider BYOK for maximum control over your API usage",
                "Enterprise customers can negotiate shorter retention periods",
            ],
        }
        
        if is_byok:
            return {
                **base_info,
                "backend": "byok",
                "data_retention": "Up to 30 days for trust & safety (application logs)",
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
                "data_retention": "Up to 30 days for trust & safety (application logs)",
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
    user_id: Optional[str] = None,
    enable_prompt_caching: bool = False,
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
        user_id: Optional hashed user ID for privacy-preserving abuse monitoring
        enable_prompt_caching: If True, enable ephemeral prompt caching
        
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
        user_id=user_id,
        enable_prompt_caching=enable_prompt_caching,
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
