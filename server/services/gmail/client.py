from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import status
from fastapi.responses import JSONResponse

from ...config import Settings, get_settings
from ...logging_config import logger
from ...models import GmailConnectPayload, GmailDisconnectPayload, GmailStatusPayload
from ...utils import error_response


_CLIENT_LOCK = threading.Lock()
_CLIENT: Optional[Any] = None

_PROFILE_CACHE: Dict[str, Dict[str, Any]] = {}
_PROFILE_CACHE_LOCK = threading.Lock()
_ACTIVE_USER_ID_LOCK = threading.Lock()
_ACTIVE_USER_ID: Optional[str] = None


def _normalized(value: Optional[str]) -> str:
    return (value or "").strip()


def _set_active_gmail_user_id(user_id: Optional[str]) -> None:
    sanitized = _normalized(user_id)
    with _ACTIVE_USER_ID_LOCK:
        global _ACTIVE_USER_ID
        old_user_id = _ACTIVE_USER_ID
        _ACTIVE_USER_ID = sanitized or None
        if old_user_id != _ACTIVE_USER_ID:
            logger.info(f"[GMAIL] Active user ID changed from '{old_user_id}' to '{_ACTIVE_USER_ID}'")


def get_active_gmail_user_id() -> Optional[str]:
    with _ACTIVE_USER_ID_LOCK:
        user_id = _ACTIVE_USER_ID
        logger.debug(f"Gmail active user ID check: {user_id}")
        return user_id


def get_all_connected_gmail_users() -> List[Tuple[str, str]]:
    """
    Get all users with active Gmail connections.
    
    Returns:
        List of (user_id, composio_user_id) tuples for each connected Gmail account
    """
    logger.info("[GET_ALL_CONNECTED] Starting to query all Gmail connections")
    try:
        client = _get_composio_client()
        # Query all Gmail accounts without status filter to see actual statuses
        logger.debug("[GET_ALL_CONNECTED] Calling connected_accounts.list(toolkit_slugs=['GMAIL'])")
        items = client.connected_accounts.list(toolkit_slugs=["GMAIL"])
        
        # Parse the response
        data = getattr(items, "data", None)
        if data is None and isinstance(items, dict):
            data = items.get("data")
        
        logger.info(f"[GET_ALL_CONNECTED] Received {len(data) if data else 0} accounts from Composio")
        
        if not data:
            logger.debug("[GET_ALL_CONNECTED] No Gmail connections found")
            return []
        
        # Extract user_id pairs and filter by status
        connected_users = []
        valid_statuses = {"ACTIVE", "CONNECTED", "SUCCESS", "SUCCESSFUL", "COMPLETED"}
        
        for account in data:
            # Get user_id from account
            if hasattr(account, "user_id"):
                user_id = getattr(account, "user_id", None)
            elif isinstance(account, dict):
                user_id = account.get("user_id")
            else:
                continue
            
            if not user_id:
                continue
            
            # Get and log the actual status
            status = getattr(account, "status", None) or (account.get("status") if isinstance(account, dict) else None)
            logger.info(f"Gmail account found - user_id: {user_id}, status: {status}")
            
            # Only include accounts with valid statuses
            if status and status.upper() in valid_statuses:
                connected_users.append((user_id, user_id))
            else:
                logger.warning(f"Skipping Gmail account with invalid status - user_id: {user_id}, status: {status}")
        
        logger.info(f"Found {len(connected_users)} connected Gmail users")
        return connected_users
        
    except Exception as exc:
        logger.error(f"Failed to list Gmail connections: {exc}")
        return []


def _gmail_import_client():
    from composio import Composio  # type: ignore
    return Composio


# Get or create a singleton Composio client instance with thread-safe initialization
def _get_composio_client(settings: Optional[Settings] = None):
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT

    with _CLIENT_LOCK:
        if _CLIENT is None:
            resolved_settings = settings or get_settings()
            Composio = _gmail_import_client()
            api_key = resolved_settings.composio_api_key
            
            if api_key:
                # Log masked API key for debugging
                masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
                logger.info(f"[COMPOSIO] Initializing with API key: {masked_key}")
            else:
                logger.warning("[COMPOSIO] No API key provided - using default/environment")
            
            try:
                _CLIENT = Composio(api_key=api_key) if api_key else Composio()
                logger.info("[COMPOSIO] Client initialized successfully")
            except TypeError as exc:
                if api_key:
                    raise RuntimeError(
                        "Installed Composio SDK does not accept the api_key argument; upgrade the SDK or remove COMPOSIO_API_KEY."
                    ) from exc
                _CLIENT = Composio()
                logger.info("[COMPOSIO] Client initialized without explicit API key")
    return _CLIENT


def _extract_email(obj: Any) -> Optional[str]:
    """Extract email address from various object structures using multiple strategies."""
    if obj is None:
        return None
    
    # Strategy 1: Direct attribute or dict key lookup
    direct_keys = (
        "email", "email_address", "emailAddress", "user_email",
        "provider_email", "account_email",
    )
    for key in direct_keys:
        # Try as attribute
        try:
            val = getattr(obj, key, None)
            if isinstance(val, str) and "@" in val:
                return val
        except Exception:
            pass
        
        # Try as dict key
        if isinstance(obj, dict):
            val = obj.get(key)
            if isinstance(val, str) and "@" in val:
                return val
    
    if not isinstance(obj, dict):
        return None
    
    # Strategy 2: Email addresses list
    email_addresses = obj.get("emailAddresses")
    if isinstance(email_addresses, (list, tuple)):
        for entry in email_addresses:
            if isinstance(entry, str) and "@" in entry:
                return entry
            if isinstance(entry, dict):
                for key in ("value", "email", "emailAddress"):
                    candidate = entry.get(key)
                    if isinstance(candidate, str) and "@" in candidate:
                        return candidate
    
    # Strategy 3: Nested path lookup
    nested_paths = (
        ("profile", "email"),
        ("profile", "emailAddress"),
        ("user", "email"),
        ("data", "email"),
        ("data", "user", "email"),
        ("provider_profile", "email"),
    )
    for path in nested_paths:
        current: Any = obj
        for segment in path:
            if isinstance(current, dict):
                current = current.get(segment)
            else:
                current = None
                break
        if isinstance(current, str) and "@" in current:
            return current
    
    return None


def _cache_profile(user_id: str, profile: Dict[str, Any]) -> None:
    sanitized = _normalized(user_id)
    if not sanitized or not isinstance(profile, dict):
        return
    with _PROFILE_CACHE_LOCK:
        _PROFILE_CACHE[sanitized] = {
            "profile": profile,
            "cached_at": datetime.utcnow().isoformat(),
        }


def _get_cached_profile(user_id: Optional[str]) -> Optional[Dict[str, Any]]:
    sanitized = _normalized(user_id)
    if not sanitized:
        return None
    with _PROFILE_CACHE_LOCK:
        payload = _PROFILE_CACHE.get(sanitized)
        if payload and isinstance(payload.get("profile"), dict):
            return payload["profile"]
    return None


def _clear_cached_profile(user_id: Optional[str] = None) -> None:
    with _PROFILE_CACHE_LOCK:
        if user_id:
            _PROFILE_CACHE.pop(_normalized(user_id), None)
        else:
            _PROFILE_CACHE.clear()


def _fetch_profile_from_composio(user_id: Optional[str]) -> Optional[Dict[str, Any]]:
    sanitized = _normalized(user_id)
    if not sanitized:
        return None
    try:
        result = execute_gmail_tool("GMAIL_GET_PROFILE", sanitized, arguments={"user_id": "me"})
    except RuntimeError as exc:
        logger.warning("GMAIL_GET_PROFILE invocation failed: %s", exc)
        return None
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected error fetching Gmail profile", extra={"user_id": sanitized})
        return None

    profile: Optional[Dict[str, Any]] = None
    if isinstance(result, dict):
        if isinstance(result.get("data"), dict):
            profile = result["data"]
        elif isinstance(result.get("profile"), dict):
            profile = result["profile"]
        elif isinstance(result.get("response_data"), dict):
            profile = result["response_data"]
        elif isinstance(result.get("items"), list):
            for item in result["items"]:
                if not isinstance(item, dict):
                    continue
                data_dict = item.get("data")
                if isinstance(data_dict, dict):
                    if isinstance(data_dict.get("response_data"), dict):
                        profile = data_dict["response_data"]
                    elif isinstance(data_dict.get("profile"), dict):
                        profile = data_dict["profile"]
                    else:
                        profile = data_dict
                elif isinstance(item.get("response_data"), dict):
                    profile = item["response_data"]
                elif isinstance(item.get("profile"), dict):
                    profile = item["profile"]
                if isinstance(profile, dict):
                    break
        elif result.get("successful") is True and isinstance(result.get("result"), dict):
            profile = result.get("result")  # type: ignore[assignment]
        elif all(not isinstance(result.get(key), dict) for key in ("data", "profile", "result")):
            profile = result if result else None

    if isinstance(profile, dict):
        _cache_profile(sanitized, profile)
        return profile

    logger.warning("Received unexpected Gmail profile payload", extra={"user_id": sanitized, "raw": result})
    return None


# Start Gmail OAuth connection process and return redirect URL
def initiate_connect(payload: GmailConnectPayload, settings: Settings) -> JSONResponse:
    auth_config_id = payload.auth_config_id or settings.composio_gmail_auth_config_id or ""
    if not auth_config_id:
        return error_response(
            "Missing auth_config_id. Set COMPOSIO_GMAIL_AUTH_CONFIG_ID or pass auth_config_id.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Require user_id from authenticated context - don't use PID as fallback for security
    if not payload.user_id:
        return error_response(
            "user_id is required for Gmail connection",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    
    user_id = payload.user_id
    _set_active_gmail_user_id(user_id)
    _clear_cached_profile(user_id)
    
    try:
        client = _get_composio_client(settings)
        
        # Check if user already has a connected Gmail account
        logger.info(f"[GMAIL CONNECT] Checking for existing Gmail connections for user: {user_id}")
        try:
            existing_items = client.connected_accounts.list(
                user_ids=[user_id], 
                toolkit_slugs=["GMAIL"]
            )
            existing_data = getattr(existing_items, "data", None)
            if existing_data is None and isinstance(existing_items, dict):
                existing_data = existing_items.get("data")
            
            if existing_data:
                # User already has Gmail connected
                logger.warning(f"[GMAIL CONNECT] User {user_id} already has {len(existing_data)} Gmail account(s) connected")
                # Check if any are active/connected
                for acc in existing_data:
                    acc_status = getattr(acc, "status", None) or (acc.get("status") if isinstance(acc, dict) else None)
                    if acc_status and acc_status.upper() in {"CONNECTED", "SUCCESS", "SUCCESSFUL", "ACTIVE", "COMPLETED"}:
                        logger.info(f"[GMAIL CONNECT] Found active account, not creating duplicate")
                        return error_response(
                            "Gmail account already connected. Please refresh status to see your connection.",
                            status_code=status.HTTP_400_BAD_REQUEST,
                        )
        except Exception as e:
            logger.debug(f"[GMAIL CONNECT] Could not check existing connections: {e}")
        
        # No existing connection found, proceed with OAuth
        logger.info(f"[GMAIL CONNECT] No existing connection, initiating OAuth for user: {user_id}")
        # Allow multiple Gmail connections per user (e.g., personal + work accounts)
        req = client.connected_accounts.initiate(
            user_id=user_id, 
            auth_config_id=auth_config_id,
            allow_multiple=True
        )
        redirect_url = getattr(req, "redirect_url", None) or getattr(req, "redirectUrl", None)
        connection_request_id = getattr(req, "id", None)
        
        data = {
            "ok": True,
            "redirect_url": redirect_url,
            "connection_request_id": connection_request_id,
            "user_id": user_id,
        }
        logger.info(f"[GMAIL CONNECT] OAuth initiated successfully")
        logger.info(f"[GMAIL CONNECT] Redirect URL: {redirect_url}")
        logger.info(f"[GMAIL CONNECT] Connection Request ID: {connection_request_id}")
        logger.info(f"[GMAIL CONNECT] After OAuth, Composio will callback to the URL configured in auth_config: {auth_config_id}")
        return JSONResponse(data)
    except Exception as exc:
        logger.exception("gmail connect failed", extra={"user_id": user_id})
        return error_response(
            "Failed to initiate Gmail connect",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


# Check Gmail connection status and retrieve user account information
def fetch_status(payload: GmailStatusPayload) -> JSONResponse:
    connection_request_id = _normalized(payload.connection_request_id)
    user_id = _normalized(payload.user_id)
    
    logger.info(f"[FETCH_STATUS] Starting - connection_request_id: {connection_request_id}, user_id: {user_id}")

    if not connection_request_id and not user_id:
        logger.warning("[FETCH_STATUS] Missing both connection_request_id and user_id")
        return error_response(
            "Missing connection_request_id or user_id",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        client = _get_composio_client()
        logger.debug(f"[FETCH_STATUS] Composio client initialized")
        account: Any = None
        
        if connection_request_id:
            logger.info(f"[FETCH_STATUS] Attempting to get account by connection_request_id: {connection_request_id}")
            try:
                account = client.connected_accounts.wait_for_connection(connection_request_id, timeout=2.0)
                logger.info(f"[FETCH_STATUS] Got account via wait_for_connection")
            except Exception as e:
                logger.debug(f"[FETCH_STATUS] wait_for_connection failed: {e}")
                try:
                    account = client.connected_accounts.get(connection_request_id)
                    logger.info(f"[FETCH_STATUS] Got account via get()")
                except Exception as e2:
                    logger.debug(f"[FETCH_STATUS] get() also failed: {e2}")
                    account = None
                    
        if account is None and user_id:
            logger.info(f"[FETCH_STATUS] Account not found by connection_request_id, trying user_id: {user_id}")
            try:
                # First, try querying ALL connected accounts (no filters at all)
                logger.info(f"[FETCH_STATUS] Step 1: Querying ALL connected accounts (no filters)")
                all_accounts_items = client.connected_accounts.list()
                all_accounts_data = getattr(all_accounts_items, "data", None)
                if all_accounts_data is None and isinstance(all_accounts_items, dict):
                    all_accounts_data = all_accounts_items.get("data")
                
                logger.info(f"[FETCH_STATUS] Found {len(all_accounts_data) if all_accounts_data else 0} total connected accounts (all toolkits)")
                if all_accounts_data:
                    for idx, acc in enumerate(all_accounts_data):
                        acc_user_id = getattr(acc, "user_id", None) or (acc.get("user_id") if isinstance(acc, dict) else None)
                        acc_status = getattr(acc, "status", None) or (acc.get("status") if isinstance(acc, dict) else None)
                        acc_id = getattr(acc, "id", None) or (acc.get("id") if isinstance(acc, dict) else None)
                        acc_app = getattr(acc, "appName", None) or (acc.get("appName") if isinstance(acc, dict) else None)
                        logger.info(f"[FETCH_STATUS]   All[{idx}]: user_id='{acc_user_id}', app='{acc_app}', status='{acc_status}', id='{acc_id}'")
                
                # Try to get the specific account we know exists: ca__Yfxvi5lltQ6
                logger.info(f"[FETCH_STATUS] Step 1.5: Trying to get account by ID: ca__Yfxvi5lltQ6")
                try:
                    specific_account = client.connected_accounts.get("ca__Yfxvi5lltQ6")
                    if specific_account:
                        logger.info(f"[FETCH_STATUS] ✓ Successfully retrieved account ca__Yfxvi5lltQ6 directly!")
                        acc_user_id = getattr(specific_account, "user_id", None) or (specific_account.get("user_id") if isinstance(specific_account, dict) else None)
                        acc_status = getattr(specific_account, "status", None) or (specific_account.get("status") if isinstance(specific_account, dict) else None)
                        logger.info(f"[FETCH_STATUS] Direct query result: user_id='{acc_user_id}', status='{acc_status}'")
                        if acc_user_id == user_id:
                            account = specific_account
                            logger.info(f"[FETCH_STATUS] ✓ Using directly retrieved account")
                except Exception as e:
                    logger.warning(f"[FETCH_STATUS] Could not retrieve account ca__Yfxvi5lltQ6: {e}")
                
                # Now try querying Gmail-specific accounts
                logger.info(f"[FETCH_STATUS] Step 2: Querying ALL Gmail accounts (toolkit filter)")
                all_items = client.connected_accounts.list(toolkit_slugs=["GMAIL"])
                all_data = getattr(all_items, "data", None)
                if all_data is None and isinstance(all_items, dict):
                    all_data = all_items.get("data")
                
                logger.info(f"[FETCH_STATUS] Found {len(all_data) if all_data else 0} Gmail-specific accounts")
                if all_data:
                    for idx, acc in enumerate(all_data):
                        acc_user_id = getattr(acc, "user_id", None) or (acc.get("user_id") if isinstance(acc, dict) else None)
                        acc_status = getattr(acc, "status", None) or (acc.get("status") if isinstance(acc, dict) else None)
                        acc_id = getattr(acc, "id", None) or (acc.get("id") if isinstance(acc, dict) else None)
                        logger.info(f"[FETCH_STATUS]   Gmail[{idx}]: user_id='{acc_user_id}', status='{acc_status}', id='{acc_id}'")
                        # Check if this account matches our user
                        if acc_user_id == user_id:
                            account = acc
                            logger.info(f"[FETCH_STATUS] ✓ Found matching account for user_id: {user_id}")
                else:
                    logger.warning(f"[FETCH_STATUS] No Gmail accounts found in Composio")
                
                # Now try the user_ids filter to see if it works
                logger.info(f"[FETCH_STATUS] Now trying with user_ids filter: [{user_id}]")
                items = client.connected_accounts.list(
                    user_ids=[user_id], toolkit_slugs=["GMAIL"]
                )
                logger.debug(f"[FETCH_STATUS] Got response from connected_accounts.list with user_ids filter")
                
                data = getattr(items, "data", None)
                if data is None and isinstance(items, dict):
                    data = items.get("data")
                    
                logger.info(f"[FETCH_STATUS] With user_ids filter: Found {len(data) if data else 0} Gmail accounts")
                
                if data and account is None:
                    # Only use filtered result if we didn't find it in the ALL query
                    account = data[0]
                    found_status = getattr(account, "status", None) or (account.get("status") if isinstance(account, dict) else None)
                    logger.info(f"[FETCH_STATUS] Using first account from filtered query - status: {found_status}")
                elif not data and account is None:
                    logger.warning(f"[FETCH_STATUS] No Gmail accounts found for user {user_id} even with both queries")
            except Exception as e:
                logger.error(f"[FETCH_STATUS] Error listing connected accounts: {e}", exc_info=True)
                account = None
        status_value = None
        email = None
        connected = False
        profile: Optional[Dict[str, Any]] = None
        profile_source = "none"

        account_user_id = None
        if account is not None:
            logger.info(f"[FETCH_STATUS] Processing account object")
            status_value = getattr(account, "status", None) or (account.get("status") if isinstance(account, dict) else None)
            normalized_status = (status_value or "").upper()
            connected = normalized_status in {"CONNECTED", "SUCCESS", "SUCCESSFUL", "ACTIVE", "COMPLETED"}
            email = _extract_email(account)
            logger.info(f"[FETCH_STATUS] Account details - status: {status_value}, normalized: {normalized_status}, connected: {connected}, email: {email}")
            if hasattr(account, "user_id"):
                account_user_id = getattr(account, "user_id", None)
            elif isinstance(account, dict):
                account_user_id = account.get("user_id")
        else:
            logger.warning(f"[FETCH_STATUS] No account object found - cannot determine connection status")

        if not user_id and account_user_id:
            user_id = _normalized(account_user_id)
            logger.debug(f"[FETCH_STATUS] Using account_user_id as user_id: {user_id}")

        if connected and user_id:
            logger.info(f"[FETCH_STATUS] Account is connected, fetching profile for user: {user_id}")
            cached_profile = _get_cached_profile(user_id)
            if cached_profile:
                profile = cached_profile
                profile_source = "cache"
            else:
                fetched_profile = _fetch_profile_from_composio(user_id)
                if fetched_profile:
                    profile = fetched_profile
                    profile_source = "fetched"
            if profile and not email:
                email = _extract_email(profile)
        elif user_id:
            _clear_cached_profile(user_id)

        _set_active_gmail_user_id(user_id)
        
        response_data = {
            "ok": True,
            "connected": bool(connected),
            "status": status_value or "UNKNOWN",
            "email": email,
            "user_id": user_id,
            "profile": profile,
            "profile_source": profile_source,
        }
        logger.info(f"[FETCH_STATUS] Returning response - connected: {connected}, status: {status_value or 'UNKNOWN'}, email: {email}, user_id: {user_id}")

        return JSONResponse(response_data)
    except Exception as exc:
        logger.exception(
            "gmail status failed",
            extra={
                "connection_request_id": connection_request_id,
                "user_id": user_id,
            },
        )
        return error_response(
            "Failed to fetch connection status",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )


def disconnect_account(payload: GmailDisconnectPayload) -> JSONResponse:
    connection_id = _normalized(payload.connection_id) or _normalized(payload.connection_request_id)
    user_id = _normalized(payload.user_id)

    if not connection_id and not user_id:
        return error_response(
            "Missing connection_id or user_id",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        client = _get_composio_client()
    except Exception as exc:
        logger.exception("gmail disconnect failed: client init", extra={"user_id": user_id})
        return error_response(
            "Failed to disconnect Gmail",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    removed_ids: list[str] = []
    errors: list[str] = []
    affected_user_ids: set[str] = set()

    def _delete_connection(identifier: str) -> None:
        sanitized_id = _normalized(identifier)
        if not sanitized_id:
            return
        try:
            connection = client.connected_accounts.get(sanitized_id)
        except Exception:
            connection = None
        try:
            client.connected_accounts.delete(sanitized_id)
            removed_ids.append(sanitized_id)
            if connection is not None:
                if hasattr(connection, "user_id"):
                    affected_user_ids.add(_normalized(getattr(connection, "user_id", None)))
                elif isinstance(connection, dict):
                    affected_user_ids.add(_normalized(connection.get("user_id")))
        except Exception as exc:  # pragma: no cover - depends on remote state
            logger.exception("Failed to remove Gmail connection", extra={"connection_id": sanitized_id})
            errors.append(str(exc))

    if connection_id:
        _delete_connection(connection_id)
    else:
        try:
            items = client.connected_accounts.list(user_ids=[user_id], toolkit_slugs=["GMAIL"])
            data = getattr(items, "data", None)
            if data is None and isinstance(items, dict):
                data = items.get("data")
        except Exception as exc:  # pragma: no cover - dependent on SDK
            logger.exception("Failed to list Gmail connections", extra={"user_id": user_id})
            return error_response(
                "Failed to disconnect Gmail",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            )

        if data:
            for entry in data:
                candidate = None
                candidate_user_id = None
                if hasattr(entry, "id"):
                    candidate = getattr(entry, "id", None)
                    candidate_user_id = getattr(entry, "user_id", None)
                if candidate is None and isinstance(entry, dict):
                    candidate = entry.get("id")
                    candidate_user_id = entry.get("user_id")
                if candidate:
                    if candidate_user_id:
                        affected_user_ids.add(_normalized(candidate_user_id))
                    _delete_connection(candidate)

    if user_id:
        affected_user_ids.add(user_id)

    for uid in list(affected_user_ids):
        if uid:
            _clear_cached_profile(uid)
            if get_active_gmail_user_id() == uid:
                _set_active_gmail_user_id(None)

    if errors and not removed_ids:
        return error_response(
            "Failed to disconnect Gmail",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="; ".join(errors),
        )

    payload = {
        "ok": True,
        "disconnected": bool(removed_ids),
        "removed_connection_ids": removed_ids,
    }
    if not removed_ids:
        payload["message"] = "No Gmail connection found"

    if errors:
        payload["warnings"] = errors
    return JSONResponse(payload)


def _normalize_tool_response(result: Any) -> Dict[str, Any]:
    payload_dict: Optional[Dict[str, Any]] = None
    try:
        if hasattr(result, "model_dump"):
            payload_dict = result.model_dump()  # type: ignore[assignment]
        elif hasattr(result, "dict"):
            payload_dict = result.dict()  # type: ignore[assignment]
    except Exception:
        payload_dict = None

    if payload_dict is None:
        try:
            if hasattr(result, "model_dump_json"):
                payload_dict = json.loads(result.model_dump_json())
        except Exception:
            payload_dict = None

    if payload_dict is None:
        if isinstance(result, dict):
            payload_dict = result
        elif isinstance(result, list):
            payload_dict = {"items": result}
        else:
            payload_dict = {"repr": str(result)}

    return payload_dict


# Execute Gmail operations through Composio SDK with error handling
def execute_gmail_tool(
    tool_name: str,
    composio_user_id: str,
    *,
    arguments: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    logger.info(
        "Executing Gmail tool",
        extra={"tool": tool_name, "user_id": composio_user_id}
    )
    logger.debug(
        "Gmail tool raw arguments",
        extra={"tool": tool_name, "arguments": arguments}
    )
    
    prepared_arguments: Dict[str, Any] = {}
    if isinstance(arguments, dict):
        for key, value in arguments.items():
            if value is not None:
                prepared_arguments[key] = value

    prepared_arguments.setdefault("user_id", "me")
    logger.debug(
        "Gmail tool prepared arguments",
        extra={"tool": tool_name, "prepared_arguments": prepared_arguments}
    )

    try:
        client = _get_composio_client()
        
        result = client.client.tools.execute(
            tool_name,
            user_id=composio_user_id,
            arguments=prepared_arguments,
        )
        
        logger.info(
            "Gmail tool execution completed",
            extra={"tool": tool_name, "user_id": composio_user_id}
        )
        normalized_result = _normalize_tool_response(result)
        logger.debug(
            "Gmail tool normalized result",
            extra={"tool": tool_name, "result_keys": list(normalized_result.keys()) if isinstance(normalized_result, dict) else None}
        )
        return normalized_result
        
    except Exception as exc:
        logger.exception(
            "Gmail tool execution failed",
            extra={"tool": tool_name, "user_id": composio_user_id, "arguments": prepared_arguments, "error": str(exc)},
        )
        raise RuntimeError(f"{tool_name} invocation failed: {exc}") from exc
