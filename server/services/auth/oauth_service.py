"""OAuth service for Google authentication."""

from __future__ import annotations

import secrets
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional
from urllib.parse import urlencode

from httpx import AsyncClient

from ...config import get_settings
from ...logging_config import logger


class OAuthStateStore:
    """
    Store and validate OAuth state parameters for CSRF protection.
    
    NOTE: This uses in-memory storage. For production with multiple servers,
    use Redis or a database for shared state across instances.
    """
    
    def __init__(self):
        self._states: Dict[str, Dict] = {}
        self._lock = threading.Lock()
    
    def create_state(self) -> str:
        """Generate and store a new state token."""
        state = secrets.token_urlsafe(32)
        
        with self._lock:
            self._states[state] = {
                "created_at": datetime.utcnow(),
                "used": False
            }
            # Cleanup old states to prevent memory leak
            self._cleanup_expired_states()
        
        logger.debug(f"Created OAuth state token")
        return state
    
    def validate_and_consume_state(self, state: str) -> bool:
        """
        Validate state parameter and mark as used (one-time use).
        Returns True if valid, False otherwise.
        """
        with self._lock:
            # Check if state exists
            if state not in self._states:
                logger.warning("OAuth state not found - possible CSRF attack")
                return False
            
            state_data = self._states[state]
            
            # Check if already used
            if state_data.get("used"):
                logger.warning("OAuth state already used - possible replay attack")
                return False
            
            # Check if expired (5 minute window)
            age = datetime.utcnow() - state_data["created_at"]
            if age > timedelta(minutes=5):
                # Remove expired state
                del self._states[state]
                logger.warning(f"OAuth state expired (age: {age.total_seconds():.1f}s)")
                return False
            
            # Mark as used and validate
            state_data["used"] = True
            logger.debug("OAuth state validated successfully")
            return True
    
    def _cleanup_expired_states(self):
        """Remove states older than 10 minutes to prevent memory leaks."""
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        expired_states = [
            state for state, data in self._states.items()
            if data["created_at"] < cutoff
        ]
        for state in expired_states:
            self._states.pop(state, None)
        
        if expired_states:
            logger.debug(f"Cleaned up {len(expired_states)} expired OAuth states")


class OAuthService:
    """OAuth service for handling Google authentication."""
    
    def __init__(self):
        self.settings = get_settings()
        self.google_client_id = self.settings.oauth_google_client_id
        self.google_client_secret = self.settings.oauth_google_client_secret
        self.redirect_uri = self.settings.oauth_redirect_uri
        
        # Log what was loaded (without exposing secrets)
        logger.info(f"OAuth Service initialized:")
        logger.info(f"  - Client ID: {'✓ Set' if self.google_client_id else '✗ MISSING'}")
        logger.info(f"  - Client Secret: {'✓ Set' if self.google_client_secret else '✗ MISSING'}")
        logger.info(f"  - Redirect URI: {self.redirect_uri if self.redirect_uri else '✗ MISSING'}")
        
        if not all([self.google_client_id, self.google_client_secret, self.redirect_uri]):
            logger.warning("OAuth configuration incomplete - authentication will not work")
    
    def get_authorization_url(self, state: str) -> str:
        """Generate Google OAuth authorization URL."""
        if not self.google_client_id:
            raise ValueError("Google OAuth client ID not configured")
        
        params = {
            "client_id": self.google_client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "openid email profile",
            "response_type": "code",
            "state": state,
            "access_type": "offline",
            "prompt": "consent"
        }
        
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        logger.debug(f"Generated OAuth URL for state: {state}")
        return auth_url
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, str]:
        """Exchange authorization code for access token."""
        # Add detailed logging for debugging
        missing = []
        if not self.google_client_id:
            missing.append("OAUTH_GOOGLE_CLIENT_ID")
        if not self.google_client_secret:
            missing.append("OAUTH_GOOGLE_CLIENT_SECRET")
        if not self.redirect_uri:
            missing.append("OAUTH_REDIRECT_URI")
        
        if missing:
            error_msg = f"OAuth configuration incomplete. Missing: {', '.join(missing)}"
            logger.error(error_msg)
            logger.error(f"Current values - Client ID exists: {bool(self.google_client_id)}, "
                        f"Client Secret exists: {bool(self.google_client_secret)}, "
                        f"Redirect URI: {self.redirect_uri}")
            raise ValueError(error_msg)
        
        async with AsyncClient() as client:
            token_data = {
                "client_id": self.google_client_id,
                "client_secret": self.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
            }
            
            logger.debug(f"Attempting token exchange with redirect_uri: {self.redirect_uri}")
            
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                raise ValueError(f"Token exchange failed: {response.status_code}")
            
            token_response = response.json()
            logger.debug("Successfully exchanged code for token")
            return token_response
    
    async def get_user_info(self, access_token: str) -> Dict[str, str]:
        """Get user information from Google using access token."""
        async with AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers=headers
            )
            
            if response.status_code != 200:
                logger.error(f"User info fetch failed: {response.status_code} - {response.text}")
                raise ValueError(f"User info fetch failed: {response.status_code}")
            
            user_info = response.json()
            logger.debug(f"Retrieved user info for: {user_info.get('email', 'unknown')}")
            return user_info
    
    def generate_state(self) -> str:
        """Generate a random state string for CSRF protection."""
        return secrets.token_urlsafe(32)


# Global instances
_oauth_service = OAuthService()
_oauth_state_store = OAuthStateStore()


def get_oauth_service() -> OAuthService:
    """Get the singleton OAuth service instance."""
    return _oauth_service


def get_oauth_state_store() -> OAuthStateStore:
    """Get the singleton OAuth state store instance."""
    return _oauth_state_store


__all__ = ["OAuthService", "get_oauth_service", "OAuthStateStore", "get_oauth_state_store"]

