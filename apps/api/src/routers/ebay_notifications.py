"""
eBay Marketplace Account Deletion Notification Endpoint

Required by eBay to keep API keys active. Handles:
- GET: Challenge verification (SHA256 hash response)
- POST: Account deletion notifications

Docs: https://developer.ebay.com/develop/guides-v2/marketplace-user-account-deletion
"""

import os
import hashlib
import logging
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ebay", tags=["ebay-notifications"])


class DeletionNotificationData(BaseModel):
    """eBay account deletion notification data"""
    username: Optional[str] = None
    userId: Optional[str] = None
    eiasToken: Optional[str] = None


class DeletionNotification(BaseModel):
    """eBay account deletion notification payload"""
    metadata: Optional[Dict[str, Any]] = None
    notification: Optional[Dict[str, Any]] = None


@router.get("/account-deletion")
async def ebay_challenge_verification(request: Request, challenge_code: str):
    """
    Handle eBay's GET challenge for endpoint verification.
    
    eBay sends: GET /ebay/account-deletion?challenge_code=<code>
    
    Response must be JSON with SHA256 hash of:
    challenge_code + verification_token + endpoint_url
    """
    verification_token = os.getenv("EBAY_VERIFICATION_TOKEN")
    
    if not verification_token:
        logger.error("EBAY_VERIFICATION_TOKEN not configured")
        raise HTTPException(
            status_code=500, 
            detail="Verification token not configured"
        )
    
    # Get the full endpoint URL (without query params)
    endpoint_url = str(request.url).split('?')[0]
    
    # Compute SHA256 hash: challenge_code + verification_token + endpoint_url
    hash_input = f"{challenge_code}{verification_token}{endpoint_url}".encode('utf-8')
    response_hash = hashlib.sha256(hash_input).hexdigest()
    
    logger.info(f"eBay challenge received. Endpoint: {endpoint_url}")
    
    # Return JSON with challengeResponse (exact field name required by eBay)
    return {"challengeResponse": response_hash}


@router.post("/account-deletion")
async def ebay_deletion_notification(request: Request):
    """
    Handle eBay account deletion notifications.
    
    eBay sends POST with JSON payload when a user deletes their account.
    Must respond with 200, 201, 202, or 204 to acknowledge.
    
    eBay retries for up to 24 hours if not acknowledged.
    """
    try:
        payload = await request.json()
        
        # Log the notification (in production, process/store as needed)
        logger.info(f"eBay deletion notification received: {payload}")
        
        # Extract notification data if present
        notification_data = payload.get("notification", {}).get("data", {})
        
        if notification_data:
            username = notification_data.get("username")
            user_id = notification_data.get("userId")
            eias_token = notification_data.get("eiasToken")
            
            logger.info(
                f"Account deletion for user: {username}, "
                f"userId: {user_id}, eiasToken: {eias_token}"
            )
            
            # TODO: Implement actual data deletion logic here
            # - Remove user data from database
            # - Clear cached user information
            # - Log deletion for compliance
            
        # Return 200 OK to acknowledge receipt
        return {}
        
    except Exception as e:
        logger.error(f"Error processing eBay deletion notification: {e}")
        # Still return 200 to prevent eBay retries
        # Log error for investigation
        return {}


@router.get("/account-deletion/health")
async def notification_endpoint_health():
    """Health check for the notification endpoint"""
    token_configured = bool(os.getenv("EBAY_VERIFICATION_TOKEN"))
    
    return {
        "status": "ok",
        "verification_token_configured": token_configured,
        "endpoint": "/api/ebay/account-deletion"
    }
