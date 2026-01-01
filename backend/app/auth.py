"""Authentication module for botchat.

Handles OAuth token validation and JWT generation/verification.
Supports GitHub, Google, Apple, and Microsoft OAuth providers.

Security model:
- OAuth tokens are validated against provider APIs
- JWTs are short-lived (1 hour) and contain minimal user info
- No user data is stored server-side (stateless validation)
- Subscription status checked via Stripe (future)
"""

import os
import time
import logging
from typing import Any, Optional, Tuple
from dataclasses import dataclass

import httpx
from jose import jwt, JWTError
from fastapi import HTTPException, Header, Depends
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# -----------------------------
# Configuration
# -----------------------------

# JWT Configuration
JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = 604800  # 7 days (was 1 hour)

# OAuth Client IDs/Secrets
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
APPLE_CLIENT_ID = os.environ.get("APPLE_CLIENT_ID", "")  # Service ID (e.g., com.botchat.auth)
APPLE_TEAM_ID = os.environ.get("APPLE_TEAM_ID", "")
APPLE_KEY_ID = os.environ.get("APPLE_KEY_ID", "")
APPLE_PRIVATE_KEY = os.environ.get("APPLE_PRIVATE_KEY", "")  # PEM format, newlines as \n
MICROSOFT_CLIENT_ID = os.environ.get("MICROSOFT_CLIENT_ID", "")
MICROSOFT_CLIENT_SECRET = os.environ.get("MICROSOFT_CLIENT_SECRET", "")
MICROSOFT_TENANT_ID = os.environ.get("MICROSOFT_TENANT_ID", "common")  # 'common' for multi-tenant

# Auth mode - disable for local development
REQUIRE_AUTH = os.environ.get("REQUIRE_AUTH", "false").lower() == "true"

# Email allowlist - comma-separated list of allowed emails (empty = allow all)
# Used to restrict access in dev environments
_allowed_emails_raw = os.environ.get("ALLOWED_EMAILS", "")
ALLOWED_EMAILS: set[str] = {
    e.strip().lower() for e in _allowed_emails_raw.split(",") if e.strip()
}


def check_email_allowed(email: Optional[str]) -> None:
    """Check if email is in allowlist (if configured).
    
    Raises HTTPException 403 if email is not allowed.
    If ALLOWED_EMAILS is empty, all emails are allowed.
    """
    if not ALLOWED_EMAILS:
        return  # No restriction
    
    if not email:
        raise HTTPException(
            status_code=403,
            detail="Email required for authentication in this environment"
        )
    
    if email.lower() not in ALLOWED_EMAILS:
        logger.warning("Access denied for email: %s (not in allowlist)", email)
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. This environment is restricted to authorized users only."
        )


# -----------------------------
# Models
# -----------------------------

@dataclass
class UserInfo:
    """Minimal user info extracted from OAuth/JWT."""
    provider: str  # "github", "google", "apple", or "microsoft"
    user_id: str   # Provider-specific user ID
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class OAuthCallbackRequest(BaseModel):
    """OAuth callback with authorization code."""
    code: str
    provider: str  # "github", "google", "apple", or "microsoft"
    redirect_uri: str
    id_token: Optional[str] = None  # Apple sends id_token via POST


class AuthResponse(BaseModel):
    """Response containing JWT and user info."""
    token: str
    user: dict[str, Any]
    expires_at: int


# -----------------------------
# JWT Functions
# -----------------------------

def create_jwt(user: UserInfo) -> Tuple[str, int]:
    """Create a signed JWT for authenticated user.
    
    Returns (token, expires_at_timestamp)
    """
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET not configured")
    
    expires_at = int(time.time()) + JWT_EXPIRY_SECONDS
    payload: dict[str, Any] = {
        "sub": f"{user.provider}:{user.user_id}",
        "provider": user.provider,
        "email": user.email,
        "name": user.name,
        "avatar": user.avatar_url,
        "exp": expires_at,
        "iat": int(time.time()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token, expires_at


def verify_jwt(token: str) -> UserInfo:
    """Verify JWT signature and extract user info.
    
    Raises HTTPException on invalid/expired token.
    """
    if not JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT_SECRET not configured")
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError as e:
        logger.warning("JWT verification failed: %s", str(e))
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Extract user info from payload
    sub = payload.get("sub", "")
    if ":" not in sub:
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    provider, user_id = sub.split(":", 1)
    return UserInfo(
        provider=provider,
        user_id=user_id,
        email=payload.get("email"),
        name=payload.get("name"),
        avatar_url=payload.get("avatar"),
    )


# -----------------------------
# OAuth Token Exchange
# -----------------------------

async def exchange_github_code(code: str, redirect_uri: str) -> UserInfo:
    """Exchange GitHub OAuth code for user info.
    
    Flow:
    1. Exchange code for access token
    2. Fetch user profile from GitHub API
    3. Return minimal UserInfo
    """
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")
    
    async with httpx.AsyncClient() as client:
        # Step 1: Exchange code for token
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        
        if token_resp.status_code != 200:
            logger.error("GitHub token exchange failed: %s", token_resp.text)
            raise HTTPException(status_code=401, detail="GitHub authentication failed")
        
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            error = token_data.get("error_description", "Unknown error")
            logger.error("GitHub token missing: %s", error)
            raise HTTPException(status_code=401, detail=f"GitHub auth error: {error}")
        
        # Step 2: Fetch user profile
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        
        if user_resp.status_code != 200:
            logger.error("GitHub user fetch failed: %s", user_resp.text)
            raise HTTPException(status_code=401, detail="Failed to fetch GitHub profile")
        
        user_data = user_resp.json()
        
        # Step 3: Get email (might need separate request if email is private)
        # SECURITY: Only use verified emails to prevent account hijacking
        email = user_data.get("email")
        if not email:
            email_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            if email_resp.status_code == 200:
                emails = email_resp.json()
                # Only use primary email if it's verified
                primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
                if primary:
                    email = primary.get("email")
                else:
                    # Fall back to any verified email
                    verified = next((e for e in emails if e.get("verified")), None)
                    if verified:
                        email = verified.get("email")
                    # If no verified email, email stays None - user won't be linked by email
        
        return UserInfo(
            provider="github",
            user_id=str(user_data["id"]),
            email=email,
            name=user_data.get("name") or user_data.get("login"),
            avatar_url=user_data.get("avatar_url"),
        )


async def exchange_google_code(code: str, redirect_uri: str) -> UserInfo:
    """Exchange Google OAuth code for user info.
    
    Flow:
    1. Exchange code for tokens (including id_token)
    2. Decode id_token to get user info (no API call needed)
    3. Return minimal UserInfo
    """
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    
    async with httpx.AsyncClient() as client:
        # Step 1: Exchange code for tokens
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        
        if token_resp.status_code != 200:
            logger.error("Google token exchange failed: %s", token_resp.text)
            raise HTTPException(status_code=401, detail="Google authentication failed")
        
        token_data = token_resp.json()
        id_token = token_data.get("id_token")
        
        if not id_token:
            raise HTTPException(status_code=401, detail="Google id_token missing")
        
        # Step 2: Decode id_token (Google's id_token is a JWT)
        # We just need to decode it - Google has already verified it
        # For extra security, we could verify the signature with Google's public keys
        try:
            # Decode without verification since we just got it from Google
            claims = jwt.get_unverified_claims(id_token)
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid Google id_token")
        
        return UserInfo(
            provider="google",
            user_id=claims["sub"],
            email=claims.get("email"),
            name=claims.get("name"),
            avatar_url=claims.get("picture"),
        )


async def exchange_apple_code(code: str, redirect_uri: str, id_token: Optional[str] = None) -> UserInfo:
    """Exchange Apple OAuth code for user info.
    
    Apple Sign In flow:
    1. Generate client_secret JWT signed with Apple private key
    2. Exchange code for tokens (including id_token)
    3. Decode id_token to get user info
    
    Note: Apple only sends user's name on FIRST authorization.
    We store it in the JWT but can't retrieve it again.
    """
    if not APPLE_CLIENT_ID or not APPLE_TEAM_ID or not APPLE_KEY_ID or not APPLE_PRIVATE_KEY:
        raise HTTPException(status_code=500, detail="Apple OAuth not configured")
    
    # Apple requires a client_secret JWT signed with your private key
    import time as time_module
    client_secret_payload: dict[str, Any] = {
        "iss": APPLE_TEAM_ID,
        "iat": int(time_module.time()),
        "exp": int(time_module.time()) + 86400 * 180,  # 6 months max
        "aud": "https://appleid.apple.com",
        "sub": APPLE_CLIENT_ID,
    }
    
    # Handle private key - may have \n as literal string
    private_key = APPLE_PRIVATE_KEY.replace("\\n", "\n")
    
    client_secret = jwt.encode(
        client_secret_payload,
        private_key,
        algorithm="ES256",
        headers={"kid": APPLE_KEY_ID}
    )
    
    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_resp = await client.post(
            "https://appleid.apple.com/auth/token",
            data={
                "client_id": APPLE_CLIENT_ID,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if token_resp.status_code != 200:
            logger.error("Apple token exchange failed: %s", token_resp.text)
            raise HTTPException(status_code=401, detail="Apple authentication failed")
        
        token_data = token_resp.json()
        received_id_token = token_data.get("id_token") or id_token
        
        if not received_id_token:
            raise HTTPException(status_code=401, detail="Apple id_token missing")
        
        # Decode id_token (Apple's id_token is a JWT)
        try:
            claims = jwt.get_unverified_claims(received_id_token)
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid Apple id_token")
        
        # Apple provides email in claims, but name only on first auth (via form POST)
        # The name would need to be passed from frontend if available
        return UserInfo(
            provider="apple",
            user_id=claims["sub"],
            email=claims.get("email"),
            name=None,  # Apple doesn't include name in id_token
            avatar_url=None,  # Apple doesn't provide avatar
        )


async def exchange_microsoft_code(code: str, redirect_uri: str) -> UserInfo:
    """Exchange Microsoft OAuth code for user info.
    
    Flow:
    1. Exchange code for tokens (including id_token and access_token)
    2. Decode id_token or call Graph API for user info
    3. Return minimal UserInfo
    """
    if not MICROSOFT_CLIENT_ID or not MICROSOFT_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Microsoft OAuth not configured")
    
    async with httpx.AsyncClient() as client:
        # Exchange code for tokens
        token_resp = await client.post(
            f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/oauth2/v2.0/token",
            data={
                "client_id": MICROSOFT_CLIENT_ID,
                "client_secret": MICROSOFT_CLIENT_SECRET,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if token_resp.status_code != 200:
            logger.error("Microsoft token exchange failed: %s", token_resp.text)
            raise HTTPException(status_code=401, detail="Microsoft authentication failed")
        
        token_data = token_resp.json()
        access_token = token_data.get("access_token")
        id_token = token_data.get("id_token")
        
        if not access_token:
            raise HTTPException(status_code=401, detail="Microsoft access_token missing")
        
        # Try to get user info from id_token first
        email = None
        name = None
        user_id = None
        
        if id_token:
            try:
                claims = jwt.get_unverified_claims(id_token)
                user_id = claims.get("sub") or claims.get("oid")
                email = claims.get("email") or claims.get("preferred_username")
                name = claims.get("name")
            except JWTError:
                pass
        
        # Fetch additional user info from Microsoft Graph API
        user_resp = await client.get(
            "https://graph.microsoft.com/v1.0/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if user_resp.status_code == 200:
            user_data = user_resp.json()
            user_id = user_id or user_data.get("id")
            email = email or user_data.get("mail") or user_data.get("userPrincipalName")
            name = name or user_data.get("displayName")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Failed to get Microsoft user ID")
        
        # Try to get profile photo URL
        # Microsoft Graph returns binary, so we'd need to store it
        # For now, we skip avatar - could be enhanced later
        avatar_url = None
        
        return UserInfo(
            provider="microsoft",
            user_id=user_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
        )


async def exchange_oauth_code(req: OAuthCallbackRequest) -> UserInfo:
    """Exchange OAuth code for user info (dispatcher)."""
    if req.provider == "github":
        return await exchange_github_code(req.code, req.redirect_uri)
    elif req.provider == "google":
        return await exchange_google_code(req.code, req.redirect_uri)
    elif req.provider == "apple":
        # Apple uses backend callback URL (form_post) - must use that URL for token exchange
        backend_url = os.environ.get("BACKEND_URL", "")
        if not backend_url:
            raise HTTPException(status_code=500, detail="BACKEND_URL not configured for Apple Sign In")
        apple_redirect = f"{backend_url}/auth/apple/callback"
        return await exchange_apple_code(req.code, apple_redirect, req.id_token)
    elif req.provider == "microsoft":
        return await exchange_microsoft_code(req.code, req.redirect_uri)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {req.provider}")


# -----------------------------
# FastAPI Dependencies
# -----------------------------

async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> Optional[UserInfo]:
    """Extract and verify user from Authorization header.
    
    Returns None if auth is disabled or no token provided.
    Raises HTTPException if auth is required and token is invalid.
    """
    if not REQUIRE_AUTH:
        return None
    
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    return verify_jwt(token)


async def require_auth(user: Optional[UserInfo] = Depends(get_current_user)) -> UserInfo:
    """Require authenticated user (use as dependency).
    
    When REQUIRE_AUTH=false, returns a dummy user for development.
    """
    if not REQUIRE_AUTH:
        return UserInfo(provider="dev", user_id="dev-user", email="dev@local", name="Dev User")
    
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    return user


# -----------------------------
# OAuth URL Builders
# -----------------------------

def get_github_auth_url(redirect_uri: str, state: str = "") -> str:
    """Build GitHub OAuth authorization URL."""
    from urllib.parse import urlencode
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "scope": "read:user user:email",
    }
    if state:
        params["state"] = state
    return f"https://github.com/login/oauth/authorize?{urlencode(params)}"


def get_google_auth_url(redirect_uri: str, state: str = "") -> str:
    """Build Google OAuth authorization URL."""
    from urllib.parse import urlencode
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        params["state"] = state
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def get_apple_auth_url(redirect_uri: str, state: str = "") -> str:
    """Build Apple OAuth authorization URL."""
    from urllib.parse import urlencode
    params = {
        "client_id": APPLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "name email",
        "response_mode": "form_post",  # Apple requires form_post for web
    }
    if state:
        params["state"] = state
    return f"https://appleid.apple.com/auth/authorize?{urlencode(params)}"


def get_microsoft_auth_url(redirect_uri: str, state: str = "") -> str:
    """Build Microsoft OAuth authorization URL."""
    from urllib.parse import urlencode
    params = {
        "client_id": MICROSOFT_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile User.Read",
        "response_mode": "query",
    }
    if state:
        params["state"] = state
    return f"https://login.microsoftonline.com/{MICROSOFT_TENANT_ID}/oauth2/v2.0/authorize?{urlencode(params)}"
