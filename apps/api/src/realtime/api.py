"""
WebSocket API endpoint for CampusAgent.

Provides the /api/v1/ws endpoint for real-time communication.

Authentication:
- Uses access_token Cookie (no URL tokens).
- Validates JWT signature, expiry, and user status.
- Origin whitelist enforcement (CSWH protection).

Client commands:
- conversation.subscribe
- conversation.unsubscribe
- ping

Server events:
- connection.established
- conversation.subscribed
- conversation.unsubscribed
- pong
- error
- message.created (pushed)

Privacy:
- No token, cookie, or message content in logs.
- Only IDs, types, and status are logged.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from ..config import Settings, settings
from ..modules.auth.tokens import TokenType, decode_token
from ..modules.users.models import User, UserStatus
from ..modules.users.repository import UserRepository
from .connection_manager import connection_manager
from .events import build_error_event, serialize_event

logger = logging.getLogger("campus_agent.realtime.api")

router = APIRouter(tags=["realtime"])

# Allowed origins for WebSocket connections
ALLOWED_ORIGINS = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # Test origins
    "http://testserver",
    "http://test",
}


def validate_origin(origin: str | None) -> bool:
    """Validate the Origin header against the whitelist.

    Per WEBSOCKET_CONTRACT.md §1.3:
    - Missing Origin: reject
    - null Origin: reject
    - Not in whitelist: reject
    """
    if origin is None:
        return False
    if origin == "null":
        return False
    return origin in ALLOWED_ORIGINS


def authenticate_websocket(websocket: WebSocket, settings_obj: Settings) -> User | None:
    """Authenticate a WebSocket connection using the access_token Cookie.

    Returns the User if authenticated, None otherwise.
    """
    access_token = websocket.cookies.get("access_token")
    if not access_token:
        return None

    try:
        payload = decode_token(access_token, settings_obj)
    except Exception:
        return None

    if payload.get("typ") != TokenType.ACCESS.value:
        return None

    user_id_str = str(payload.get("sub", ""))
    if not user_id_str:
        return None

    try:
        user_uuid = UUID(user_id_str)
    except (ValueError, TypeError):
        return None

    # We need a DB session to look up the user
    session_factory = getattr(websocket.app.state, "db_sessionmaker", None)
    if session_factory is None:
        return None

    session = session_factory()
    try:
        user = UserRepository(session).get_by_id(user_uuid)
        if user is None:
            return None
        if user.status in (UserStatus.DISABLED.value, UserStatus.DELETED.value):
            return None
        return user
    finally:
        session.close()


@router.websocket("/api/v1/ws")
async def websocket_endpoint(
    websocket: WebSocket,
) -> None:
    """Main WebSocket endpoint.

    Authentication via access_token Cookie.
    Origin whitelist enforcement.
    """
    # Origin validation
    origin = websocket.headers.get("origin")
    if not validate_origin(origin):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning(
            "ws.origin_rejected",
            extra={"origin": origin},
        )
        return

    # Authentication
    settings_obj = settings
    user = authenticate_websocket(websocket, settings_obj)
    if user is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("ws.auth_failed", extra={"origin": origin})
        return

    # Accept connection
    info = await connection_manager.connect(websocket, user)

    try:
        while True:
            raw = await websocket.receive_text()
            await _handle_client_message(websocket, info, raw)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error(
            "ws.error",
            extra={
                "connection_id": info.connection_id,
                "user_id": str(user.id),
                "error": str(exc),
            },
        )
    finally:
        await connection_manager.disconnect(info.connection_id)


async def _handle_client_message(
    websocket: WebSocket,
    info: Any,
    raw: str,
) -> None:
    """Handle a client message."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        await _send_error(info, "WS_INVALID_MESSAGE", "Invalid JSON message")
        return

    event = msg.get("event")
    data = msg.get("data", {})
    request_id = msg.get("request_id")

    if not event:
        await _send_error(info, "WS_MISSING_EVENT", "Missing event field")
        return

    if event == "conversation.subscribe":
        conversation_id_str = data.get("conversation_id")
        if not conversation_id_str:
            await _send_error(info, "WS_MISSING_FIELD", "Missing conversation_id", request_id)
            return
        try:
            conversation_id = UUID(conversation_id_str)
        except (ValueError, TypeError):
            await _send_error(info, "WS_INVALID_FIELD", "Invalid conversation_id", request_id)
            return

        # Get a DB session for authorization
        session_factory = getattr(websocket.app.state, "db_sessionmaker", None)
        if session_factory is None:
            await _send_error(info, "WS_INTERNAL_ERROR", "Database not available", request_id)
            return

        session = session_factory()
        try:
            await connection_manager.handle_subscribe(
                info, conversation_id, request_id, session
            )
        finally:
            session.close()

    elif event == "conversation.unsubscribe":
        conversation_id_str = data.get("conversation_id")
        if not conversation_id_str:
            await _send_error(info, "WS_MISSING_FIELD", "Missing conversation_id", request_id)
            return
        try:
            conversation_id = UUID(conversation_id_str)
        except (ValueError, TypeError):
            await _send_error(info, "WS_INVALID_FIELD", "Invalid conversation_id", request_id)
            return

        await connection_manager.handle_unsubscribe(info, conversation_id, request_id)

    elif event == "ping":
        await connection_manager.handle_ping(info, request_id)

    else:
        await _send_error(info, "WS_UNKNOWN_EVENT", f"Unknown event: {event}", request_id)


async def _send_error(info: Any, code: str, message: str, request_id: str | None = None) -> None:
    """Send an error event to a connection."""

    event = build_error_event(
        error_code=code,
        message=message,
        sequence=info.next_sequence(),
        request_id=request_id,
    )
    await info.websocket.send_text(serialize_event(event))
