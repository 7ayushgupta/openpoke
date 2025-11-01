from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import get_settings
from .logging_config import configure_logging, logger
from .routes import api_router
from .services import get_watcher_manager, get_trigger_scheduler
from .llm_client.client import _log_provider_initialization
from .migrations.migrate_to_multiuser import run_migration


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP to HTTPS in production (when behind a reverse proxy)."""
    
    async def dispatch(self, request: Request, call_next):
        # Check if we're in production and request came via HTTP
        env = os.getenv("ENVIRONMENT", "development")
        
        # Only redirect in production
        if env == "production":
            # Check X-Forwarded-Proto header (set by reverse proxy)
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
            
            # If request came via HTTP, redirect to HTTPS
            if forwarded_proto == "http":
                url = request.url.replace(scheme="https")
                logger.info(f"Redirecting HTTP to HTTPS: {request.url} -> {url}")
                return JSONResponse(
                    status_code=status.HTTP_301_MOVED_PERMANENTLY,
                    content={"detail": "Redirecting to HTTPS"},
                    headers={"Location": str(url)}
                )
        
        return await call_next(request)


# Register global exception handlers for consistent error responses across the API
def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def _validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.debug("validation error", extra={"errors": exc.errors(), "path": str(request.url)})
        return JSONResponse(
            {"ok": False, "error": "Invalid request", "detail": exc.errors()},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(HTTPException)
    async def _http_exception_handler(request: Request, exc: HTTPException):
        logger.debug(
            f"http error: {exc.status_code} {exc.detail} at {request.url}",
            extra={"detail": exc.detail, "status": exc.status_code, "path": str(request.url)},
        )
        detail = exc.detail
        if not isinstance(detail, str):
            detail = json.dumps(detail)
        return JSONResponse({"ok": False, "error": detail}, status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled error", extra={"path": str(request.url)})
        return JSONResponse(
            {"ok": False, "error": "Internal server error"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan with startup and shutdown logic."""
    # Startup
    logger.info("🚀 Starting OpenPoke Server...")
    _settings = get_settings()
    logger.info(f"📦 Version: {_settings.app_version}")
    logger.info(f"🌐 Server: {_settings.server_host}:{_settings.server_port}")
    _log_provider_initialization()
    
    # Run migration first
    logger.info("Running multi-user migration...")
    migration_success = run_migration()
    if not migration_success:
        logger.error("Migration failed, but continuing startup")
    
    # Start background services
    scheduler = get_trigger_scheduler()
    await scheduler.start()
    
    # Start multi-user Gmail watcher manager
    watcher_manager = get_watcher_manager()
    await watcher_manager.start()
    
    logger.info("✅ OpenPoke Server startup complete")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down OpenPoke Server...")
    await scheduler.stop()
    await watcher_manager.stop()
    
    # Close HTTP client connection pool
    from .llm_client.client import _close_http_client
    await _close_http_client()
    
    logger.info("✅ OpenPoke Server shutdown complete")


configure_logging()
_settings = get_settings()

app = FastAPI(
    title=_settings.app_name,
    version=_settings.app_version,
    docs_url=_settings.resolved_docs_url,
    redoc_url=None,
    lifespan=lifespan,
)

# Add HTTPS redirect middleware (only active in production)
app.add_middleware(HTTPSRedirectMiddleware)

# Configure CORS with secure settings
logger.info(f"🔒 CORS configured for origins: {_settings.cors_allow_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_allow_origins,
    allow_credentials=True,  # Enable credentials (cookies, authorization headers)
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Be specific about methods
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],  # Be specific about headers
    expose_headers=["Content-Length", "X-Request-ID"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

register_exception_handlers(app)
app.include_router(api_router)


__all__ = ["app"]
