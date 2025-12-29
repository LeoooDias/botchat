"""
API key verification for different providers.

Tests that an API key is valid by making a minimal API call.
"""

import httpx
from typing import Tuple, Optional


async def verify_openai_key(api_key: str) -> Tuple[bool, str, Optional[dict]]:
    """Verify an OpenAI API key.
    
    Returns:
        (is_valid, message, details)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get("data", []))
                return True, f"Valid! Access to {model_count} models.", {"models": model_count}
            elif response.status_code == 401:
                return False, "Invalid API key.", None
            elif response.status_code == 429:
                # Rate limited but key is valid
                return True, "Valid (rate limited - try again later).", None
            else:
                return False, f"Unexpected response: {response.status_code}", None
                
    except httpx.TimeoutException:
        return False, "Connection timeout - check your internet.", None
    except Exception as e:
        return False, f"Connection error: {str(e)}", None


async def verify_anthropic_key(api_key: str) -> Tuple[bool, str, Optional[dict]]:
    """Verify an Anthropic API key.
    
    Returns:
        (is_valid, message, details)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Use the messages API with a minimal request to verify the key
            # We'll catch the error for invalid model, but the auth check happens first
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "Hi"}]
                }
            )
            
            if response.status_code == 200:
                return True, "Valid! API key verified.", None
            elif response.status_code == 401:
                return False, "Invalid API key.", None
            elif response.status_code == 403:
                error = response.json().get("error", {})
                message = error.get("message", "Access denied")
                return False, message, None
            elif response.status_code == 429:
                # Rate limited but key is valid
                return True, "Valid (rate limited - try again later).", None
            elif response.status_code == 400:
                # Bad request usually means auth passed
                error = response.json().get("error", {})
                message = error.get("message", "")
                if "credit" in message.lower() or "billing" in message.lower():
                    return False, "API key valid but no credits. Add billing in Anthropic Console.", {"billing_required": True}
                # Other 400 errors after auth = key is valid
                return True, "Valid! API key verified.", None
            else:
                return False, f"Unexpected response: {response.status_code}", None
                
    except httpx.TimeoutException:
        return False, "Connection timeout - check your internet.", None
    except Exception as e:
        return False, f"Connection error: {str(e)}", None


async def verify_gemini_key(api_key: str) -> Tuple[bool, str, Optional[dict]]:
    """Verify a Google Gemini API key.
    
    Returns:
        (is_valid, message, details)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
            )
            
            if response.status_code == 200:
                data = response.json()
                model_count = len(data.get("models", []))
                return True, f"Valid! Access to {model_count} models.", {"models": model_count}
            elif response.status_code == 400:
                error = response.json().get("error", {})
                message = error.get("message", "Invalid request")
                if "API key not valid" in message:
                    return False, "Invalid API key.", None
                return False, message, None
            elif response.status_code == 403:
                error = response.json().get("error", {})
                message = error.get("message", "Access denied")
                if "billing" in message.lower():
                    return False, "API key valid but billing not enabled. Enable billing in Google Cloud Console.", {"billing_required": True}
                return False, message, None
            else:
                return False, f"Unexpected response: {response.status_code}", None
                
    except httpx.TimeoutException:
        return False, "Connection timeout - check your internet.", None
    except Exception as e:
        return False, f"Connection error: {str(e)}", None


async def verify_provider_key(provider: str, api_key: str) -> Tuple[bool, str, Optional[dict]]:
    """Verify an API key for any supported provider.
    
    Args:
        provider: Provider name (openai, gemini, anthropic)
        api_key: The API key to verify
        
    Returns:
        (is_valid, message, details)
    """
    provider = provider.lower()
    
    if provider == "openai":
        return await verify_openai_key(api_key)
    elif provider == "gemini":
        return await verify_gemini_key(api_key)
    elif provider == "anthropic":
        return await verify_anthropic_key(api_key)
    else:
        return False, f"Unknown provider: {provider}", None
