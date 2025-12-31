"""
AI Provider implementations for botchat.

This module provides direct integrations with AI providers, replacing
the msgmodel dependency for better control, privacy, and flexibility.

v2.2.0: Gemini via Vertex AI (platform) and AI Studio (BYOK)
v2.3.0: Anthropic direct integration (planned)
v2.4.0: OpenAI direct integration (planned)
"""

from app.providers.gemini import (
    GeminiProvider,
    stream_gemini,
    get_gemini_privacy_info,
)

__all__ = [
    "GeminiProvider",
    "stream_gemini", 
    "get_gemini_privacy_info",
]
