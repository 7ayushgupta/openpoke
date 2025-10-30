"""Authentication routes for OAuth login."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from ..logging_config import logger
from ..models.auth import User, UserCreate, UserResponse
from ..middleware.auth import get_current_user
from ..services.auth.oauth_service import get_oauth_service
from ..services.auth.jwt_service import get_jwt_service
from ..services.auth.user_store import get_user_store

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/login")
async def login() -> Dict[str, str]:
    """Initiate OAuth login flow."""
    oauth_service = get_oauth_service()
    
    try:
        # Generate state for CSRF protection
        state = oauth_service.generate_state()
        
        # Generate authorization URL
        auth_url = oauth_service.get_authorization_url(state)
        
        logger.info(f"OAuth login initiated with state: {state}")
        return {
            "auth_url": auth_url,
            "state": state
        }
    except Exception as exc:
        logger.error(f"OAuth login failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth login failed"
        )


@router.get("/callback")
async def oauth_callback(
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: str = Query(..., description="State parameter for CSRF protection")
) -> Dict[str, str]:
    """Handle OAuth callback and create user session."""
    oauth_service = get_oauth_service()
    jwt_service = get_jwt_service()
    user_store = get_user_store()
    
    try:
        # Exchange code for token
        token_response = await oauth_service.exchange_code_for_token(code)
        access_token = token_response.get("access_token")
        
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No access token received"
            )
        
        # Get user info from Google
        user_info = await oauth_service.get_user_info(access_token)
        email = user_info.get("email")
        name = user_info.get("name", "")
        
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No email received from OAuth provider"
            )
        
        # Check if user exists, create if not
        user = user_store.get_user_by_email(email)
        if user is None:
            # Generate user ID from email
            user_id = email.split("@")[0].replace(".", "_").replace("+", "_")
            
            # Ensure unique user ID
            counter = 1
            original_user_id = user_id
            while user_store.user_exists(user_id):
                user_id = f"{original_user_id}_{counter}"
                counter += 1
            
            user = user_store.create_user(UserCreate(
                id=user_id,
                email=email,
                provider="google"
            ))
            logger.info(f"Created new user: {email} ({user_id})")
        else:
            logger.info(f"Existing user logged in: {email} ({user.id})")
        
        # Create JWT token
        jwt_token = jwt_service.create_access_token(user.id, user.email)
        
        logger.info(f"OAuth callback successful for user: {email}")
        return {
            "access_token": jwt_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"OAuth callback failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth callback failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> UserResponse:
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        provider=current_user.provider,
        created_at=current_user.created_at
    )


@router.post("/logout")
async def logout() -> Dict[str, str]:
    """Logout endpoint (client-side token removal)."""
    # JWT tokens are stateless, so we just return success
    # The client should remove the token from storage
    return {"message": "Logged out successfully"}


__all__ = ["router"]

