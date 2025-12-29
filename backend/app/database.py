"""Database module for botchat.

Handles PostgreSQL connection and user/subscription storage.
Uses minimal data storage - only what's required for billing.

Tables:
- users: OAuth identity + Stripe customer ID + subscription status + quota tracking
"""

import os
import secrets
import logging
from typing import Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import asyncpg
from asyncpg import Pool

logger = logging.getLogger(__name__)


def generate_encryption_key() -> str:
    """Generate a strong encryption key for client-side key encryption."""
    return secrets.token_hex(32)  # 256-bit key

# Database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Connection pool (initialized on startup)
_pool: Optional[Pool] = None


# -----------------------------
# Connection Management
# -----------------------------

async def init_db():
    """Initialize database connection pool and create tables."""
    global _pool
    
    if not DATABASE_URL:
        logger.warning("DATABASE_URL not set - billing features disabled")
        return
    
    try:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info("Database connection pool created")
        
        # Create tables if they don't exist
        await _create_tables()
        
    except Exception as e:
        logger.error("Failed to initialize database: %s", str(e))
        raise


async def close_db():
    """Close database connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


async def _create_tables():
    """Create required tables if they don't exist."""
    if not _pool:
        return
    
    async with _pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                oauth_provider VARCHAR(20) NOT NULL,
                oauth_id VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                stripe_customer_id VARCHAR(255),
                subscription_status VARCHAR(20) DEFAULT 'none',
                subscription_id VARCHAR(255),
                subscription_ends_at TIMESTAMP,
                encryption_key VARCHAR(64),
                message_quota_used INT DEFAULT 0,
                quota_period_start TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(oauth_provider, oauth_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_users_stripe_customer 
                ON users(stripe_customer_id);
            
            CREATE INDEX IF NOT EXISTS idx_users_oauth 
                ON users(oauth_provider, oauth_id);
            
            CREATE INDEX IF NOT EXISTS idx_users_email
                ON users(LOWER(email));
        """)
        
        # Add encryption_key column if it doesn't exist (migration for existing DBs)
        await conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'encryption_key'
                ) THEN
                    ALTER TABLE users ADD COLUMN encryption_key VARCHAR(64);
                END IF;
            END $$;
        """)
        
        # Add quota columns if they don't exist (migration for existing DBs)
        await conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'message_quota_used'
                ) THEN
                    ALTER TABLE users ADD COLUMN message_quota_used INT DEFAULT 0;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'quota_period_start'
                ) THEN
                    ALTER TABLE users ADD COLUMN quota_period_start TIMESTAMP DEFAULT NOW();
                END IF;
            END $$;
        """)
        
        logger.info("Database tables created/verified")


def get_pool() -> Optional[Pool]:
    """Get the database connection pool."""
    return _pool


# -----------------------------
# User Operations
# -----------------------------

async def get_user_by_oauth(provider: str, oauth_id: str) -> Optional[dict]:
    """Get user by OAuth provider and ID."""
    if not _pool:
        return None
    
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, oauth_provider, oauth_id, email, stripe_customer_id,
                   subscription_status, subscription_id, subscription_ends_at,
                   encryption_key, message_quota_used, quota_period_start,
                   created_at, updated_at
            FROM users
            WHERE oauth_provider = $1 AND oauth_id = $2
            """,
            provider, oauth_id
        )
        return dict(row) if row else None


async def get_user_by_stripe_customer(customer_id: str) -> Optional[dict]:
    """Get user by Stripe customer ID."""
    if not _pool:
        return None
    
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, oauth_provider, oauth_id, email, stripe_customer_id,
                   subscription_status, subscription_id, subscription_ends_at,
                   encryption_key, message_quota_used, quota_period_start,
                   created_at, updated_at
            FROM users
            WHERE stripe_customer_id = $1
            """,
            customer_id
        )
        return dict(row) if row else None


async def get_user_by_email(email: str) -> Optional[dict]:
    """Get user by email address (for linking OAuth accounts)."""
    if not _pool or not email:
        return None
    
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, oauth_provider, oauth_id, email, stripe_customer_id,
                   subscription_status, subscription_id, subscription_ends_at,
                   encryption_key, message_quota_used, quota_period_start,
                   created_at, updated_at
            FROM users
            WHERE LOWER(email) = LOWER($1)
            """,
            email
        )
        return dict(row) if row else None


async def get_user_for_billing(provider: str, oauth_id: str, email: Optional[str] = None) -> Optional[dict]:
    """Get user for billing purposes, with email-based account linking.
    
    Lookup order:
    1. Exact OAuth match (provider + oauth_id)
    2. Email match (if provided) - allows sharing subscription across OAuth providers
    
    This ensures users can sign in via GitHub OR Google and access the same subscription.
    """
    # First try exact OAuth match
    user = await get_user_by_oauth(provider, oauth_id)
    if user:
        return user
    
    # Try email match (allows cross-provider subscription access)
    if email:
        user = await get_user_by_email(email)
        if user:
            logger.info(
                "Billing lookup: %s via %s found existing account by email (provider: %s)",
                email, provider, user['oauth_provider']
            )
            return user
    
    return None


async def create_user(provider: str, oauth_id: str, email: Optional[str] = None) -> dict:
    """Create a new user, or return existing user by email.
    
    Email-based account linking:
    - If a user with this email already exists, return that user (keeps subscription)
    - This allows users to sign in with GitHub OR Google and share the same account
    - The original OAuth provider/id is preserved (first one registered)
    """
    if not _pool:
        raise RuntimeError("Database not initialized")
    
    # First, check if this exact OAuth identity exists
    existing = await get_user_by_oauth(provider, oauth_id)
    if existing:
        # Same provider + ID, just update email if needed
        # Also generate encryption_key if missing (migration for existing users)
        async with _pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE users
                SET email = COALESCE($3, email), 
                    encryption_key = COALESCE(encryption_key, $4),
                    updated_at = NOW()
                WHERE oauth_provider = $1 AND oauth_id = $2
                RETURNING id, oauth_provider, oauth_id, email, stripe_customer_id,
                          subscription_status, subscription_id, subscription_ends_at,
                          encryption_key, message_quota_used, quota_period_start,
                          created_at, updated_at
                """,
                provider, oauth_id, email, generate_encryption_key()
            )
            return dict(row)
    
    # Check if a user with this email already exists (different provider)
    # Return existing user to share subscription across OAuth providers
    if email:
        existing_by_email = await get_user_by_email(email)
        if existing_by_email:
            logger.info(
                "Email linking: %s signing in via %s, found existing account (provider: %s)",
                email, provider, existing_by_email['oauth_provider']
            )
            # Return existing user - they share the subscription!
            return existing_by_email
    
    # No existing user - create new with encryption key
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (oauth_provider, oauth_id, email, encryption_key)
            VALUES ($1, $2, $3, $4)
            RETURNING id, oauth_provider, oauth_id, email, stripe_customer_id,
                      subscription_status, subscription_id, subscription_ends_at,
                      encryption_key, message_quota_used, quota_period_start,
                      created_at, updated_at
            """,
            provider, oauth_id, email, generate_encryption_key()
        )
        return dict(row)


async def update_user_stripe_customer(
    provider: str, 
    oauth_id: str, 
    stripe_customer_id: str
) -> Optional[dict]:
    """Update user's Stripe customer ID."""
    if not _pool:
        return None
    
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE users
            SET stripe_customer_id = $3, updated_at = NOW()
            WHERE oauth_provider = $1 AND oauth_id = $2
            RETURNING id, oauth_provider, oauth_id, email, stripe_customer_id,
                      subscription_status, subscription_id, subscription_ends_at,
                      created_at, updated_at
            """,
            provider, oauth_id, stripe_customer_id
        )
        return dict(row) if row else None


async def update_subscription_status(
    stripe_customer_id: str,
    status: str,
    subscription_id: Optional[str] = None,
    ends_at: Optional[datetime] = None
) -> Optional[dict]:
    """Update user's subscription status by Stripe customer ID."""
    if not _pool:
        return None
    
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE users
            SET subscription_status = $2,
                subscription_id = $3,
                subscription_ends_at = $4,
                updated_at = NOW()
            WHERE stripe_customer_id = $1
            RETURNING id, oauth_provider, oauth_id, email, stripe_customer_id,
                      subscription_status, subscription_id, subscription_ends_at,
                      created_at, updated_at
            """,
            stripe_customer_id, status, subscription_id, ends_at
        )
        return dict(row) if row else None


async def get_subscription_status(provider: str, oauth_id: str, email: Optional[str] = None) -> dict:
    """Get user's subscription status with email-based account linking.
    
    Returns a dict with:
    - status: 'none' | 'trialing' | 'active' | 'canceled' | 'past_due'
    - is_subscribed: bool (true if trialing or active)
    - ends_at: Optional datetime
    
    Uses email-based lookup to allow subscription sharing across OAuth providers.
    """
    # Use email-aware lookup for cross-provider subscription access
    user = await get_user_for_billing(provider, oauth_id, email)
    
    if not user:
        return {
            "status": "none",
            "is_subscribed": False,
            "ends_at": None,
        }
    
    status = user.get("subscription_status", "none")
    is_subscribed = status in ("trialing", "active")
    
    # Check if subscription has ended
    ends_at = user.get("subscription_ends_at")
    if ends_at and datetime.now() > ends_at:
        is_subscribed = False
    
    return {
        "status": status,
        "is_subscribed": is_subscribed,
        "ends_at": ends_at.isoformat() if ends_at else None,
    }


# -----------------------------
# Quota Management
# -----------------------------

# Quota limits
FREE_TIER_QUOTA = 100  # messages per month for free users
PAID_TIER_QUOTA = 5000  # messages per month for paid users
QUOTA_PERIOD_DAYS = 30  # rolling period for free users


async def get_user_quota(provider: str, oauth_id: str, email: Optional[str] = None) -> dict:
    """Get user's message quota status.
    
    Returns:
    - used: messages used this period
    - limit: total allowed for this period
    - remaining: messages remaining
    - period_ends_at: when current period ends
    - is_paid: whether user has paid subscription
    """
    user = await get_user_for_billing(provider, oauth_id, email)
    
    if not user:
        return {
            "used": 0,
            "limit": FREE_TIER_QUOTA,
            "remaining": FREE_TIER_QUOTA,
            "period_ends_at": None,
            "is_paid": False,
        }
    
    # Determine if paid user
    status = user.get("subscription_status", "none")
    is_paid = status in ("trialing", "active")
    
    # Check if subscription has ended
    sub_ends_at = user.get("subscription_ends_at")
    if sub_ends_at and datetime.now() > sub_ends_at:
        is_paid = False
    
    # Determine quota limit
    limit = PAID_TIER_QUOTA if is_paid else FREE_TIER_QUOTA
    
    # Get quota period info
    quota_period_start = user.get("quota_period_start") or datetime.now()
    message_quota_used = user.get("message_quota_used") or 0
    
    # Check if period needs reset
    # For paid users: reset based on subscription_ends_at (next billing cycle)
    # For free users: 30-day rolling period from quota_period_start
    period_ends_at = None
    should_reset = False
    
    if is_paid and sub_ends_at:
        # Paid users: period aligns with subscription billing cycle
        period_ends_at = sub_ends_at
        # Check if we're past the subscription end (renewed)
        if datetime.now() > sub_ends_at:
            should_reset = True
    else:
        # Free users: 30-day rolling period
        period_ends_at = quota_period_start + timedelta(days=QUOTA_PERIOD_DAYS)
        if datetime.now() > period_ends_at:
            should_reset = True
    
    # If period expired, reset quota (will be committed on next increment)
    if should_reset:
        message_quota_used = 0
    
    remaining = max(0, limit - message_quota_used)
    
    return {
        "used": message_quota_used,
        "limit": limit,
        "remaining": remaining,
        "period_ends_at": period_ends_at.isoformat() if period_ends_at else None,
        "is_paid": is_paid,
    }


async def increment_quota(provider: str, oauth_id: str, count: int = 1) -> Optional[dict]:
    """Increment user's message quota usage.
    
    Also handles period reset if needed.
    
    Args:
        provider: OAuth provider
        oauth_id: OAuth user ID
        count: Number of messages to add (default 1)
    
    Returns:
        Updated quota info, or None if user not found
    """
    if not _pool:
        return None
    
    user = await get_user_by_oauth(provider, oauth_id)
    if not user:
        return None
    
    # Determine if paid user
    status = user.get("subscription_status", "none")
    is_paid = status in ("trialing", "active")
    sub_ends_at = user.get("subscription_ends_at")
    if sub_ends_at and datetime.now() > sub_ends_at:
        is_paid = False
    
    # Check if period needs reset
    quota_period_start = user.get("quota_period_start") or datetime.now()
    
    should_reset = False
    new_period_start = quota_period_start
    
    if is_paid and sub_ends_at:
        # Paid: check if past subscription end (billing renewed)
        if datetime.now() > sub_ends_at:
            should_reset = True
            new_period_start = datetime.now()
    else:
        # Free: 30-day rolling period
        period_ends_at = quota_period_start + timedelta(days=QUOTA_PERIOD_DAYS)
        if datetime.now() > period_ends_at:
            should_reset = True
            new_period_start = datetime.now()
    
    async with _pool.acquire() as conn:
        if should_reset:
            # Reset quota and start new period
            row = await conn.fetchrow(
                """
                UPDATE users
                SET message_quota_used = $3,
                    quota_period_start = $4,
                    updated_at = NOW()
                WHERE oauth_provider = $1 AND oauth_id = $2
                RETURNING message_quota_used, quota_period_start
                """,
                provider, oauth_id, count, new_period_start
            )
        else:
            # Increment existing quota
            row = await conn.fetchrow(
                """
                UPDATE users
                SET message_quota_used = COALESCE(message_quota_used, 0) + $3,
                    updated_at = NOW()
                WHERE oauth_provider = $1 AND oauth_id = $2
                RETURNING message_quota_used, quota_period_start
                """,
                provider, oauth_id, count
            )
    
    if not row:
        return None
    
    limit = PAID_TIER_QUOTA if is_paid else FREE_TIER_QUOTA
    used = row['message_quota_used']
    
    return {
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
        "is_paid": is_paid,
    }


async def reset_user_quota(stripe_customer_id: str) -> Optional[dict]:
    """Reset user's quota when subscription renews.
    
    Called from Stripe webhook when subscription is renewed.
    """
    if not _pool:
        return None
    
    async with _pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE users
            SET message_quota_used = 0,
                quota_period_start = NOW(),
                updated_at = NOW()
            WHERE stripe_customer_id = $1
            RETURNING id, message_quota_used, quota_period_start
            """,
            stripe_customer_id
        )
        return dict(row) if row else None
