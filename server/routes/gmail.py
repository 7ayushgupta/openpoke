from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..config import Settings, get_settings
from ..models import GmailConnectPayload, GmailDisconnectPayload, GmailStatusPayload
from ..models.auth import User
from ..middleware.auth import get_current_user
from ..services import disconnect_account, fetch_status, initiate_connect

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.post("/connect")
# Initiate Gmail OAuth connection flow through Composio
async def gmail_connect(
    payload: GmailConnectPayload, 
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings)
) -> JSONResponse:
    from ..logging_config import logger
    logger.info(f"[GMAIL CONNECT] Request received - user: {current_user.id}")
    # Use authenticated user's ID, not the payload's user_id (security)
    payload.user_id = current_user.id
    result = initiate_connect(payload, settings)
    logger.info(f"[GMAIL CONNECT] Response status: {result.status_code}")
    return result


@router.post("/status")
# Check the current Gmail connection status and user information
async def gmail_status(
    payload: GmailStatusPayload,
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    from ..logging_config import logger
    logger.info(f"[GMAIL STATUS] Request received - user: {current_user.id}, connection_request_id: {payload.connection_request_id}")
    # Use authenticated user's ID, not the payload's user_id (security)
    payload.user_id = current_user.id
    result = fetch_status(payload)
    logger.info(f"[GMAIL STATUS] Response status: {result.status_code}")
    return result


@router.post("/disconnect")
# Disconnect Gmail account and clear cached profile data
async def gmail_disconnect(
    payload: GmailDisconnectPayload,
    current_user: User = Depends(get_current_user)
) -> JSONResponse:
    # Use authenticated user's ID, not the payload's user_id (security)
    payload.user_id = current_user.id
    return disconnect_account(payload)
