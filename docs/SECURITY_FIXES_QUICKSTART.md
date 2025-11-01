# Security Fixes Quick Start Guide

**🔴 CRITICAL: DO NOT DEPLOY WITHOUT THESE FIXES**

This is a condensed guide showing exactly how to fix the **9 blocking security issues** before cloud deployment.

---

## Fix #1: Add Authentication to Admin Endpoint (5 minutes)

**File:** `server/routes/admin.py`

```python
# BEFORE (VULNERABLE):
@router.get("/status")
async def get_admin_status():
    """Get admin dashboard status..."""
    
# AFTER (SECURE):
from ..middleware.auth import get_current_user
from ..models.auth import User
from fastapi import Depends

@router.get("/status")
async def get_admin_status(
    current_user: User = Depends(get_current_user)  # ✅ Require authentication
):
    """Get admin dashboard status..."""
    # Optional: Add admin-only check
    if current_user.id != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
```

Also fix the roster call on line 24:
```python
# BEFORE:
roster = get_agent_roster()  # ❌ No user_id - exposes all users!

# AFTER:
roster = get_agent_roster(current_user.id)  # ✅ User-specific data only
```

---

## Fix #2: OAuth State Validation (30 minutes)

**File:** `server/services/auth/oauth_service.py`

Add state storage class:

```python
from datetime import datetime, timedelta
import threading

class OAuthStateStore:
    """Temporary state storage for OAuth CSRF protection."""
    
    def __init__(self):
        self._states = {}  # Use Redis in production!
        self._lock = threading.Lock()
    
    def create_state(self) -> str:
        """Generate and store a new state token."""
        state = secrets.token_urlsafe(32)
        with self._lock:
            self._states[state] = {
                "created_at": datetime.utcnow()
            }
            # Cleanup old states (prevent memory leak)
            self._cleanup_old_states()
        return state
    
    def validate_and_consume_state(self, state: str) -> bool:
        """Validate state and remove it (one-time use)."""
        with self._lock:
            if state not in self._states:
                return False
            state_data = self._states.pop(state)
            # Check if expired (5 minute window)
            age = datetime.utcnow() - state_data["created_at"]
            if age > timedelta(minutes=5):
                return False
            return True
    
    def _cleanup_old_states(self):
        """Remove states older than 10 minutes."""
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        expired = [
            state for state, data in self._states.items()
            if data["created_at"] < cutoff
        ]
        for state in expired:
            self._states.pop(state, None)

# Global instance
_oauth_state_store = OAuthStateStore()

def get_oauth_state_store() -> OAuthStateStore:
    return _oauth_state_store
```

**File:** `server/routes/auth.py`

Update login endpoint:
```python
from ..services.auth.oauth_service import get_oauth_service, get_oauth_state_store

@router.get("/login")
async def login() -> Dict[str, str]:
    oauth_service = get_oauth_service()
    state_store = get_oauth_state_store()
    
    # Create and store state
    state = state_store.create_state()  # ✅ Store it
    auth_url = oauth_service.get_authorization_url(state)
    
    return {"auth_url": auth_url, "state": state}
```

Update callback endpoint:
```python
@router.get("/callback")
async def oauth_callback(code: str, state: str) -> Dict[str, str]:
    state_store = get_oauth_state_store()
    
    # ✅ VALIDATE STATE FIRST
    if not state_store.validate_and_consume_state(state):
        logger.warning(f"Invalid OAuth state parameter")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state parameter. Please try logging in again."
        )
    
    # Now proceed with rest of OAuth flow...
    oauth_service = get_oauth_service()
    # ... existing code ...
```

---

## Fix #3: Require JWT_SECRET_KEY in Production (5 minutes)

**File:** `server/services/auth/jwt_service.py`

```python
def _get_or_generate_secret_key(self) -> str:
    secret_key = self.settings.jwt_secret_key
    
    if not secret_key:
        # ✅ FAIL LOUDLY in production
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production":
            raise RuntimeError(
                "❌ JWT_SECRET_KEY is REQUIRED in production!\n"
                "Generate one with:\n"
                "  python -c 'import secrets; print(secrets.token_urlsafe(32))'\n"
                "Then set it in your .env or environment variables."
            )
        
        # Only allow auto-generation in development
        secret_key = secrets.token_urlsafe(32)
        logger.error(
            "⚠️ JWT_SECRET_KEY not set! Using temporary key. "
            "Set JWT_SECRET_KEY environment variable before deploying."
        )
    
    return secret_key
```

**Set the environment variable:**
```bash
# Generate a secure key:
python -c 'import secrets; print(secrets.token_urlsafe(32))'

# Add to your .env file:
JWT_SECRET_KEY=your-generated-key-here

# Or set as environment variable in your cloud provider
```

---

## Fix #4: Configure CORS Properly (5 minutes)

**File:** `.env` (create if doesn't exist)

```bash
# Development
OPENPOKE_CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:8001

# Production (replace with your actual domain)
OPENPOKE_CORS_ALLOW_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

**File:** `server/app.py`

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_allow_origins,
    allow_credentials=True,  # ✅ Enable credentials for auth cookies
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # ✅ Be specific
    allow_headers=["Authorization", "Content-Type"],  # ✅ Be specific
)
```

---

## Fix #5: Enable HTTPS (10-30 minutes)

**Option A: Using Nginx Reverse Proxy (Recommended)**

```nginx
# /etc/nginx/sites-available/openpoke
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    
    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

Install Let's Encrypt certificate:
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

**Option B: Using Caddy (Automatic HTTPS)**

```caddyfile
# Caddyfile
yourdomain.com {
    reverse_proxy localhost:8001
}
```

Run: `sudo caddy run`

---

## Fix #6: Add Rate Limiting (15 minutes)

**Install slowapi:**
```bash
pip install slowapi
```

**File:** `server/app.py`

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Create limiter
limiter = Limiter(key_func=get_remote_address)

# Add to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**File:** `server/routes/chat.py`

```python
from slowapi import Limiter
from fastapi import Request

@router.post("/send")
@app.state.limiter.limit("20/minute")  # ✅ 20 messages per minute
async def chat_send(
    request: Request,
    payload: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    return await handle_chat_request(payload, user_id=current_user.id)
```

**File:** `server/routes/auth.py`

```python
@router.get("/callback")
@app.state.limiter.limit("5/minute")  # ✅ Prevent OAuth brute force
async def oauth_callback(request: Request, code: str, state: str):
    # ... existing code ...
```

**File:** `server/routes/admin.py`

```python
@router.get("/status")
@app.state.limiter.limit("10/minute")  # ✅ Prevent status endpoint abuse
async def get_admin_status(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    # ... existing code ...
```

---

## Fix #7: Shorten JWT Expiration (10 minutes)

**File:** `server/services/auth/jwt_service.py`

```python
# BEFORE:
ACCESS_TOKEN_EXPIRE_DAYS = 30  # ❌ Way too long

# AFTER:
ACCESS_TOKEN_EXPIRE_HOURS = 12  # ✅ 12 hour tokens (or use 1 hour)

def create_access_token(self, user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    # ... rest of code ...
```

*Note: For a complete solution, implement refresh tokens (see full audit document).*

---

## Fix #8: Move Tokens to HttpOnly Cookies (20 minutes)

**File:** `server/routes/auth.py`

```python
from fastapi.responses import Response

@router.get("/callback")
async def oauth_callback(
    response: Response,
    code: str,
    state: str
) -> Dict[str, str]:
    # ... existing OAuth validation code ...
    
    jwt_token = jwt_service.create_access_token(user.id, user.email)
    
    # ✅ Set httpOnly cookie instead of returning token in JSON
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,  # ✅ JavaScript cannot access
        secure=True,    # ✅ Only sent over HTTPS
        samesite="lax", # ✅ CSRF protection
        max_age=12 * 60 * 60,  # 12 hours
        domain=None,    # Set to your domain in production
    )
    
    return {
        "success": True,
        "user_id": user.id,
        "email": user.email
        # ❌ Don't return access_token in JSON anymore
    }
```

**File:** `server/middleware/auth.py`

Update to read from cookies:

```python
from fastapi import Cookie

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    access_token: Optional[str] = Cookie(None)  # ✅ Also check cookies
) -> User:
    # Try Bearer token first (for API clients)
    token = None
    if credentials:
        token = credentials.credentials
    # Fall back to cookie (for web app)
    elif access_token:
        token = access_token
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    
    # ... rest of validation code ...
```

**File:** `web/contexts/AuthContext.tsx`

Remove localStorage usage:

```typescript
// REMOVE this line:
// localStorage.setItem('openpoke_token', data.access_token);

// Cookies are set automatically by the server
// Just reload to pick up the auth state
window.location.href = '/';
```

**File:** `web/lib/api.ts`

Remove token from headers (cookies sent automatically):

```typescript
private async request<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  const url = `${API_BASE}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    credentials: 'include',  // ✅ Send cookies automatically
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
      // ❌ Remove: 'Authorization': `Bearer ${token}`
    },
  });
  
  // ... rest of code
}
```

---

## Fix #9: Add Security Headers (5 minutes)

**File:** `server/app.py`

```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Add CSP if not breaking your app:
        # response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response

# Add to app
app.add_middleware(SecurityHeadersMiddleware)
```

---

## Verification Checklist

After implementing fixes, verify:

```bash
# 1. Test admin endpoint requires auth
curl http://localhost:8001/api/v1/admin/status
# Should return 401 Unauthorized

# 2. Test OAuth state validation
# - Try reusing an OAuth callback URL
# - Should be rejected with "Invalid or expired state"

# 3. Test JWT secret key is set
grep JWT_SECRET_KEY .env
# Should show a long random string

# 4. Test CORS
curl -H "Origin: http://evil.com" http://localhost:8001/api/v1/health
# Should not have Access-Control-Allow-Origin: * in response

# 5. Test HTTPS redirect (if using nginx/caddy)
curl http://yourdomain.com
# Should return 301 redirect to https://

# 6. Test rate limiting
for i in {1..25}; do curl http://localhost:8001/api/v1/admin/status; done
# Should start returning 429 Too Many Requests after 10-20 requests

# 7. Test JWT expiration
# Wait 12 hours or temporarily set ACCESS_TOKEN_EXPIRE_HOURS = 0.001
# Token should expire and require re-authentication

# 8. Test cookie security
# Open browser DevTools → Application → Cookies
# access_token cookie should have: HttpOnly ✓, Secure ✓, SameSite Lax

# 9. Test security headers
curl -I https://yourdomain.com/api/v1/health
# Should include X-Frame-Options, X-Content-Type-Options, etc.
```

---

## Update requirements.txt

```bash
# Add to server/requirements.txt:
slowapi>=0.1.9
```

Then install:
```bash
pip install -r server/requirements.txt
```

---

## Environment Variables Checklist

**Required in Production:**
```bash
# .env or cloud environment variables
ENVIRONMENT=production
JWT_SECRET_KEY=<generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'>
OPENPOKE_CORS_ALLOW_ORIGINS=https://yourdomain.com
OPENROUTER_API_KEY=<your key>
COMPOSIO_API_KEY=<your key>
COMPOSIO_GMAIL_AUTH_CONFIG_ID=<your config>
OAUTH_GOOGLE_CLIENT_ID=<your client id>
OAUTH_GOOGLE_CLIENT_SECRET=<your client secret>
OAUTH_REDIRECT_URI=https://yourdomain.com/auth/callback
```

---

## Deployment Order

1. **Update code with all 9 fixes**
2. **Set all environment variables**
3. **Install dependencies** (`pip install -r requirements.txt`)
4. **Test locally with ENVIRONMENT=production**
5. **Set up HTTPS (nginx/caddy with Let's Encrypt)**
6. **Deploy to staging environment**
7. **Run security verification tests**
8. **Monitor logs for errors**
9. **Deploy to production**
10. **Set up monitoring and alerts**

---

## Time Estimate

| Task | Time |
|------|------|
| Fix #1: Admin auth | 5 min |
| Fix #2: OAuth state | 30 min |
| Fix #3: JWT secret | 5 min |
| Fix #4: CORS | 5 min |
| Fix #5: HTTPS | 10-30 min |
| Fix #6: Rate limiting | 15 min |
| Fix #7: JWT expiration | 10 min |
| Fix #8: HttpOnly cookies | 20 min |
| Fix #9: Security headers | 5 min |
| **Testing** | 30 min |
| **TOTAL** | **2-3 hours** |

---

## Getting Help

If you encounter issues:

1. Check logs: `tail -f server/logs/openpoke.log`
2. Test individual endpoints with curl
3. Review the full audit: `SECURITY_AUDIT.md`
4. Check FastAPI documentation: https://fastapi.tiangolo.com/
5. OAuth debugging: Check state values in logs

---

## After Deployment

1. Monitor authentication logs for failures
2. Watch for rate limit violations
3. Check SSL certificate expiration
4. Review security headers with: https://securityheaders.com/
5. Test with: https://observatory.mozilla.org/

**Next steps:** Review medium and low priority issues in `SECURITY_AUDIT.md`

