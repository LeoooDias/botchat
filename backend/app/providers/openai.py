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
import io
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


def _strip_exif_metadata(image_bytes: bytes, mime_type: str) -> bytes:
    """
    Strip EXIF metadata from images for privacy.
    
    EXIF data can contain sensitive info: GPS coordinates, device identifiers,
    timestamps, camera settings, etc. We strip it before sending to OpenAI.
    
    Args:
        image_bytes: Raw image bytes
        mime_type: Image MIME type (e.g., "image/jpeg")
        
    Returns:
        Image bytes with EXIF stripped (or original if stripping fails)
    """
    try:
        from PIL import Image
        
        # Only process supported formats
        if mime_type not in ("image/jpeg", "image/png", "image/webp", "image/heic"):
            return image_bytes
        
        # Load image
        img = Image.open(io.BytesIO(image_bytes))
        
        # Create clean copy without EXIF
        # For JPEG/WebP, re-encoding drops EXIF; for PNG, we copy pixel data only
        output = io.BytesIO()
        
        # Determine output format
        if mime_type == "image/jpeg":
            # Re-encode as JPEG without EXIF (quality 95 to minimize loss)
            img_rgb = img.convert("RGB") if img.mode != "RGB" else img
            img_rgb.save(output, format="JPEG", quality=95)
        elif mime_type == "image/png":
            # PNG: copy to new image to strip metadata chunks
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(list(img.getdata()))
            clean_img.save(output, format="PNG")
        elif mime_type == "image/webp":
            img.save(output, format="WEBP", quality=95)
        else:
            # Unsupported format, return original
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
        
        # Create client with ZDR header and minimized SDK telemetry
        # NOTE: X-OpenAI-No-Store is only honored for orgs with formal ZDR agreements
        # NOTE: X-Stainless-* headers are SDK telemetry - we suppress them for privacy
        self.client = OpenAI(
            api_key=self.api_key,
            default_headers={
                "X-OpenAI-No-Store": "true",  # Request ZDR (best-effort, not guaranteed)
                # Minimize SDK telemetry headers (privacy-forward)
                "X-Stainless-OS": "private",
                "X-Stainless-Arch": "private",
                "X-Stainless-Runtime": "private",
                "X-Stainless-Runtime-Version": "private",
                "X-Stainless-Package-Version": "private",
                "X-Stainless-Lang": "private",
            }
        )
        
        # Log which mode we're in (no key material - even prefixes are risky in logs)
        if self.is_byok:
            logger.info("🔑 BYOK MODE: Using user-provided OpenAI API key")
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
        # IMPORTANT: store=False disables OpenAI's request/response storage
        # This is the primary privacy control (X-OpenAI-No-Store is best-effort only)
        request_params: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "store": False,  # Disable application state storage
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
            # Tightened logging: avoid leaking prompts via exception strings
            # Log type + status code only; full detail goes to debug level
            status_code = getattr(e, "status_code", "n/a")
            logger.error("OpenAI streaming error (%s, status=%s)", type(e).__name__, status_code)
            logger.debug("OpenAI streaming error detail: %r", e)
            
            error_msg = str(e)
            error_lower = error_msg.lower()
            
            # Provide user-friendly error messages (sanitized - no raw error in user output)
            if "429" in error_msg or "rate" in error_lower:
                raise RateLimitError("Rate limited by OpenAI API. Please try again later.")
            elif "401" in error_msg or "invalid_api_key" in error_lower:
                raise AuthenticationError("Invalid API key. Please check your OpenAI API key.")
            elif "403" in error_msg or "permission" in error_lower:
                raise AuthenticationError("Permission denied. Your API key may lack required permissions.")
            elif "model" in error_lower and ("not found" in error_lower or "does not exist" in error_lower):
                raise ModelNotFoundError(f"Model '{model}' is not available.")
            elif "context_length" in error_lower or "maximum context" in error_lower:
                raise ContextLengthError("Message too long for this model's context window.")
            else:
                raise OpenAIAPIError("OpenAI API error. Please try again.")
    
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
                    # Strip EXIF metadata for privacy (GPS, device IDs, timestamps, etc.)
                    clean_bytes = _strip_exif_metadata(file_bytes, mime_type)
                    
                    # Base64 encode image
                    b64_data = base64.standard_b64encode(clean_bytes).decode("utf-8")
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{b64_data}",
                            "detail": "auto",  # Let OpenAI choose resolution
                        }
                    })
                    logger.debug("Added image to request: %s (%s, %d bytes, EXIF stripped)", 
                               filename, mime_type, len(clean_bytes))
            
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
                "data_retention": "Application state/logs retained up to 30 days, then removed (ZDR forces store=false if eligible)",
                "training_opt_out": True,  # API data not used for training by default
                "zdr_honored": "Only if your organization has a ZDR agreement with OpenAI",
                "enterprise_grade": False,  # Unless user has enterprise plan
                "compliance": ["SOC 2 Type 2"],
                "privacy_summary": "BYOK - store=false set, ZDR header sent (honored only with enterprise agreement)",
                "privacy_level": "medium",
                "user_action_available": "Contact OpenAI for enterprise ZDR agreement",
                "store_disabled": True,  # We always set store=false
            }
        else:
            return {
                **base_info,
                "backend": "platform",
                "data_retention": "Application state/logs retained up to 30 days, then removed",
                "training_opt_out": True,  # API data not used for training
                "zdr_honored": False,  # botchat doesn't have ZDR agreement
                "enterprise_grade": False,
                "compliance": ["SOC 2 Type 2"],
                "privacy_summary": "Platform key - store=false set, data retained up to 30 days (no ZDR agreement)",
                "privacy_level": "medium",
                "transparency_note": "botchat has not applied for OpenAI's ZDR program",
                "store_disabled": True,  # We always set store=false
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
