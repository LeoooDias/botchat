"""Billing module for botchat.

Handles Stripe integration for subscriptions:
- Checkout session creation
- Customer portal access
- Webhook processing
- Subscription status management

Stripe events handled:
- checkout.session.completed: New subscription created
- customer.subscription.created: Subscription activated
- customer.subscription.updated: Status change (trial end, renewal, etc.)
- customer.subscription.deleted: Subscription canceled
"""

import os
import logging
from typing import Optional
from datetime import datetime

import stripe
from fastapi import APIRouter, Request, HTTPException, Depends, Header
from pydantic import BaseModel

from app.auth import UserInfo, get_current_user, require_auth
from app.database import (
    get_user_for_billing,
    create_user,
    update_user_stripe_customer,
    update_subscription_status,
    get_user_by_stripe_customer,
    get_subscription_status,
    reset_user_quota,
)

logger = logging.getLogger(__name__)

# -----------------------------
# Configuration
# -----------------------------

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
else:
    logger.warning("STRIPE_SECRET_KEY not set - billing features disabled")

# Frontend URLs (for redirects)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# Router for billing endpoints
router = APIRouter(prefix="/billing", tags=["billing"])


# -----------------------------
# Request/Response Models
# -----------------------------

class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutResponse(BaseModel):
    """Response with checkout session URL."""
    checkout_url: str
    session_id: str


class PortalResponse(BaseModel):
    """Response with customer portal URL."""
    portal_url: str


class SubscriptionStatusResponse(BaseModel):
    """Response with subscription status."""
    status: str  # 'none' | 'trialing' | 'active' | 'canceled' | 'past_due'
    is_subscribed: bool
    ends_at: Optional[str] = None


class BillingConfigResponse(BaseModel):
    """Response with billing configuration."""
    publishable_key: str
    price_id: str
    enabled: bool


# -----------------------------
# Helper Functions
# -----------------------------

async def get_or_create_stripe_customer(user: UserInfo) -> str:
    """Get or create a Stripe customer for the user.
    
    Uses email-based account linking to find existing customers.
    This allows users to share a subscription across OAuth providers.
    """
    # Check if user exists in database (with email-based linking)
    db_user = await get_user_for_billing(user.provider, user.user_id, user.email)
    
    if db_user and db_user.get("stripe_customer_id"):
        logger.info(
            "Found existing Stripe customer %s for %s (via %s)",
            db_user["stripe_customer_id"], user.email, db_user["oauth_provider"]
        )
        return db_user["stripe_customer_id"]
    
    # Ensure user exists in database (create_user also does email linking)
    if not db_user:
        db_user = await create_user(user.provider, user.user_id, user.email)
        # Re-check if the linked user has a Stripe customer
        if db_user and db_user.get("stripe_customer_id"):
            return db_user["stripe_customer_id"]
    
    # Create Stripe customer (email is optional - skip if invalid/missing)
    customer_params = {
        "metadata": {
            "oauth_provider": user.provider,
            "oauth_id": user.user_id,
        },
    }
    # Only include email if it looks valid (contains @, has domain)
    if user.email and "@" in user.email and "." in user.email.split("@")[-1]:
        customer_params["email"] = user.email
    
    customer = stripe.Customer.create(**customer_params)
    
    # Update user with Stripe customer ID (use db_user's provider if linked)
    update_provider = db_user["oauth_provider"] if db_user else user.provider
    update_oauth_id = db_user["oauth_id"] if db_user else user.user_id
    await update_user_stripe_customer(update_provider, update_oauth_id, customer.id)
    
    return customer.id


def map_stripe_status(stripe_status: str) -> str:
    """Map Stripe subscription status to our simplified status."""
    mapping = {
        "trialing": "trialing",
        "active": "active",
        "canceled": "canceled",
        "past_due": "past_due",
        "unpaid": "past_due",
        "incomplete": "none",
        "incomplete_expired": "none",
        "paused": "canceled",
    }
    return mapping.get(stripe_status, "none")


# -----------------------------
# Endpoints
# -----------------------------

@router.get("/config", response_model=BillingConfigResponse)
async def get_billing_config():
    """Get billing configuration for frontend."""
    return BillingConfigResponse(
        publishable_key=STRIPE_PUBLISHABLE_KEY,
        price_id=STRIPE_PRICE_ID,
        enabled=bool(STRIPE_SECRET_KEY and STRIPE_PRICE_ID),
    )


@router.get("/status", response_model=SubscriptionStatusResponse)
async def get_status(user: UserInfo = Depends(require_auth)):
    """Get current user's subscription status (with email-based account linking)."""
    status = await get_subscription_status(user.provider, user.user_id, user.email)
    return SubscriptionStatusResponse(**status)


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    user: UserInfo = Depends(require_auth)
):
    """Create a Stripe Checkout session for subscription."""
    if not STRIPE_SECRET_KEY or not STRIPE_PRICE_ID:
        raise HTTPException(status_code=503, detail="Billing not configured")
    
    # Get or create Stripe customer
    customer_id = await get_or_create_stripe_customer(user)
    
    # Default URLs
    success_url = request.success_url or f"{FRONTEND_URL}/billing?success=true"
    cancel_url = request.cancel_url or f"{FRONTEND_URL}/billing?canceled=true"
    
    # Create checkout session
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            subscription_data={
                "trial_period_days": 7,
            },
            allow_promotion_codes=True,
        )
        
        return CheckoutResponse(
            checkout_url=session.url,
            session_id=session.id,
        )
        
    except stripe.error.StripeError as e:
        logger.error("Stripe checkout error: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(user: UserInfo = Depends(require_auth)):
    """Create a Stripe Customer Portal session for subscription management."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Billing not configured")
    
    # Get user's Stripe customer ID (with email-based account linking)
    db_user = await get_user_for_billing(user.provider, user.user_id, user.email)
    
    if not db_user or not db_user.get("stripe_customer_id"):
        raise HTTPException(status_code=400, detail="No subscription found")
    
    try:
        session = stripe.billing_portal.Session.create(
            customer=db_user["stripe_customer_id"],
            return_url=f"{FRONTEND_URL}/billing",
        )
        
        return PortalResponse(portal_url=session.url)
        
    except stripe.error.StripeError as e:
        logger.error("Stripe portal error: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to create portal session")


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events."""
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook not configured")
    
    # Get raw body for signature verification
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.error("Invalid webhook payload")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid webhook signature")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle events
    event_type = event["type"]
    data = event["data"]["object"]
    
    logger.info("Received Stripe webhook: %s", event_type)
    
    if event_type == "checkout.session.completed":
        await handle_checkout_completed(data)
    elif event_type == "customer.subscription.created":
        await handle_subscription_created(data)
    elif event_type == "customer.subscription.updated":
        await handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        await handle_subscription_deleted(data)
    else:
        logger.debug("Unhandled event type: %s", event_type)
    
    return {"status": "ok"}


# -----------------------------
# Webhook Handlers
# -----------------------------

async def handle_checkout_completed(session: dict):
    """Handle successful checkout completion."""
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    
    if not customer_id:
        logger.error("Checkout completed but no customer ID")
        return
    
    logger.info("Checkout completed for customer: %s", customer_id)
    
    # Subscription status will be updated by subscription.created event
    # But we can mark the user as subscribed here too for redundancy
    if subscription_id:
        await update_subscription_status(
            customer_id,
            status="active",  # Will be corrected by subscription event if trialing
            subscription_id=subscription_id,
        )


async def handle_subscription_created(subscription: dict):
    """Handle new subscription creation.
    
    Resets quota to give new subscribers their full paid allocation.
    """
    customer_id = subscription.get("customer")
    status = map_stripe_status(subscription.get("status", ""))
    subscription_id = subscription.get("id")
    
    # Get trial/period end
    trial_end = subscription.get("trial_end")
    current_period_end = subscription.get("current_period_end")
    
    ends_at = None
    if trial_end:
        ends_at = datetime.fromtimestamp(trial_end)
    elif current_period_end:
        ends_at = datetime.fromtimestamp(current_period_end)
    
    logger.info("Subscription created: %s, status: %s", subscription_id, status)
    
    # Reset quota for the new subscription - start fresh with paid tier limit
    reset_result = await reset_user_quota(customer_id)
    if reset_result:
        logger.info("Quota reset for new subscriber %s", customer_id)
    
    await update_subscription_status(
        customer_id,
        status=status,
        subscription_id=subscription_id,
        ends_at=ends_at,
    )


async def handle_subscription_updated(subscription: dict):
    """Handle subscription updates (renewals, trial end, etc.).
    
    This fires on:
    - Billing cycle renewal (new period starts)
    - Trial ending
    - Plan changes
    - Status changes
    
    We reset quota when a new billing period starts.
    """
    customer_id = subscription.get("customer")
    status = map_stripe_status(subscription.get("status", ""))
    subscription_id = subscription.get("id")
    
    # Get current period end
    current_period_end = subscription.get("current_period_end")
    ends_at = datetime.fromtimestamp(current_period_end) if current_period_end else None
    
    # Get previous attributes to detect billing cycle renewal
    # Stripe includes previous_attributes for changed fields
    previous_attrs = subscription.get("previous_attributes", {})
    
    logger.info("Subscription updated: %s, status: %s", subscription_id, status)
    
    # Check if billing cycle renewed (current_period_end changed)
    # This happens when a new billing period starts
    if "current_period_end" in previous_attrs:
        logger.info("Billing cycle renewed for customer %s - resetting quota", customer_id)
        reset_result = await reset_user_quota(customer_id)
        if reset_result:
            logger.info("Quota reset successful for customer %s", customer_id)
        else:
            logger.warning("Quota reset failed for customer %s - user not found", customer_id)
    
    await update_subscription_status(
        customer_id,
        status=status,
        subscription_id=subscription_id,
        ends_at=ends_at,
    )


async def handle_subscription_deleted(subscription: dict):
    """Handle subscription cancellation/deletion."""
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")
    
    logger.info("Subscription deleted: %s", subscription_id)
    
    await update_subscription_status(
        customer_id,
        status="canceled",
        subscription_id=subscription_id,
        ends_at=datetime.now(),  # Ended now
    )
