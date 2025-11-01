"""JWT token management for authentication."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from ...config import get_settings
from ...logging_config import logger
from ...models.auth import TokenData

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30


class JWTService:
    """JWT token management service."""
    
    def __init__(self):
        self.settings = get_settings()
        self.secret_key = self._get_or_generate_secret_key()
    
    def _get_or_generate_secret_key(self) -> str:
        """Get JWT secret key from settings - FAILS in production if not set."""
        secret_key = self.settings.jwt_secret_key
        
        if not secret_key:
            env = os.getenv("ENVIRONMENT", "development")
            
            # FAIL LOUDLY in production
            if env == "production":
                raise RuntimeError(
                    "\n"
                    "=" * 70 + "\n"
                    "❌ CRITICAL: JWT_SECRET_KEY is not set!\n"
                    "=" * 70 + "\n"
                    "JWT_SECRET_KEY is REQUIRED in production.\n\n"
                    "Generate a secure key with:\n"
                    "  python -c 'import secrets; print(secrets.token_urlsafe(32))'\n\n"
                    "Then set it in your environment:\n"
                    "  export JWT_SECRET_KEY='your-generated-key-here'\n"
                    "Or add to .env file:\n"
                    "  JWT_SECRET_KEY=your-generated-key-here\n"
                    "=" * 70
                )
            
            # Only allow auto-generation in development
            secret_key = secrets.token_urlsafe(32)
            logger.error(
                "⚠️  JWT_SECRET_KEY not set! Using temporary key.\n"
                "    This key will change on restart, logging out all users.\n"
                "    Set JWT_SECRET_KEY environment variable before deploying."
            )
        
        return secret_key
    
    def create_access_token(self, user_id: str, email: str) -> str:
        """Create a JWT access token."""
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
        to_encode = {
            "user_id": user_id,
            "email": email,
            "exp": expire
        }
        
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=ALGORITHM)
        logger.debug(f"Created access token for user: {email}")
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[ALGORITHM])
            user_id: str = payload.get("user_id")
            email: str = payload.get("email")
            exp: int = payload.get("exp")
            
            if user_id is None or email is None or exp is None:
                logger.warning("Invalid token payload")
                return None
            
            # Convert exp timestamp to datetime
            exp_datetime = datetime.fromtimestamp(exp)
            
            return TokenData(
                user_id=user_id,
                email=email,
                exp=exp_datetime
            )
            
        except JWTError as exc:
            logger.debug(f"JWT verification failed: {exc}")
            return None
    
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)


# Global JWT service instance
_jwt_service = JWTService()


def get_jwt_service() -> JWTService:
    """Get the singleton JWT service instance."""
    return _jwt_service


__all__ = ["JWTService", "get_jwt_service"]

