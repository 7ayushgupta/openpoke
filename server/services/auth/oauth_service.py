"""OAuth service for Google authentication."""

from __future__ import annotations

import secrets
from typing import Dict, Optional
from urllib.parse import urlencode

from httpx import AsyncClient

from ...config import get_settings
from ...logging_config import logger


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


# Global OAuth service instance
_oauth_service = OAuthService()


def get_oauth_service() -> OAuthService:
    """Get the singleton OAuth service instance."""
    return _oauth_service


__all__ = ["OAuthService", "get_oauth_service"]

