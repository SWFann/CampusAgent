"""
Conversations API routes for CampusAgent.

Provides:
- POST /api/v1/conversations/private — create/reuse private conversation (auth + CSRF)
- POST /api/v1/conversations — create group conversation (auth + CSRF)
- GET /api/v1/conversations — list conversations (auth)
- GET /api/v1/conversations/{conversation_id} — get conversation (auth)
- GET /api/v1/conversations/{conversation_id}/participants — list participants (auth)
- POST /api/v1/conversations/{conversation_id}/participants — add participant (auth + CSRF)
- DELETE /api/v1/conversations/{conversation_id}/participants/{user_id} — remove participant (auth + CSRF)
- POST /api/v1/conversations/{conversation_id}/messages — send message (auth + CSRF)
- GET /api/v1/conversations/{conversation_id}/messages — list messages (auth)
- DELETE /api/v1/conversations/{conversation_id}/messages/{message_id} — delete message (auth + CSRF)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from ...dependencies import get_db_session
from ...schemas.envelope import success
from ..auth.csrf import require_csrf
from ..auth.dependencies import get_current_user
from ..users.models import User
from . import service
from .schemas import (
    GroupConversationCreateRequest,
    MessageCreateRequest,
    ParticipantAddRequest,
    PrivateConversationCreateRequest,
)

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


# ---------------------------------------------------------------------------
# POST /api/v1/conversations/private
# ---------------------------------------------------------------------------


@router.post("/private", status_code=status.HTTP_201_CREATED)
def create_private_conversation(
    body: PrivateConversationCreateRequest,
    http_request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Create or reuse a private conversation. Auth + CSRF required."""
    result = service.create_private_conversation(
        actor=current_user,
        target_user_id=body.target_user_id,
        session=db_session,
    )
    response.headers["Location"] = f"/api/v1/conversations/{result['id']}"
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/conversations
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED)
def create_group_conversation(
    body: GroupConversationCreateRequest,
    http_request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Create a group conversation. Auth + CSRF required."""
    data = body.model_dump(exclude_unset=True)
    result = service.create_group_conversation(
        actor=current_user,
        data=data,
        session=db_session,
    )
    response.headers["Location"] = f"/api/v1/conversations/{result['id']}"
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/conversations
# ---------------------------------------------------------------------------


@router.get("", status_code=status.HTTP_200_OK)
def list_conversations(
    http_request: Request,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """List conversations for the authenticated user. Auth required."""
    result = service.list_conversations(
        actor=current_user,
        page=page,
        page_size=page_size,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/conversations/{conversation_id}
# ---------------------------------------------------------------------------


@router.get("/{conversation_id}", status_code=status.HTTP_200_OK)
def get_conversation(
    conversation_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Get a single conversation. Auth required."""
    result = service.get_conversation(
        actor=current_user,
        conversation_id=conversation_id,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/conversations/{conversation_id}/participants
# ---------------------------------------------------------------------------


@router.get(
    "/{conversation_id}/participants", status_code=status.HTTP_200_OK
)
def list_participants(
    conversation_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """List participants in a conversation. Auth required."""
    result = service.list_participants(
        actor=current_user,
        conversation_id=conversation_id,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# POST /api/v1/conversations/{conversation_id}/participants
# ---------------------------------------------------------------------------


@router.post(
    "/{conversation_id}/participants", status_code=status.HTTP_201_CREATED
)
def add_participant(
    conversation_id: UUID,
    body: ParticipantAddRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Add a participant to a conversation. Auth + CSRF required."""
    result = service.add_participant(
        actor=current_user,
        conversation_id=conversation_id,
        target_user_id=body.user_id,
        target_role=body.role,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/conversations/{conversation_id}/participants/{user_id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{conversation_id}/participants/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_participant(
    conversation_id: UUID,
    user_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> Response:
    """Remove a participant from a conversation. Auth + CSRF required."""
    service.remove_participant(
        actor=current_user,
        conversation_id=conversation_id,
        target_user_id=user_id,
        session=db_session,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# POST /api/v1/conversations/{conversation_id}/messages
# ---------------------------------------------------------------------------


@router.post(
    "/{conversation_id}/messages", status_code=status.HTTP_201_CREATED
)
def create_message(
    conversation_id: UUID,
    body: MessageCreateRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> dict[str, Any]:
    """Send a message to a conversation. Auth + CSRF required."""
    data = body.model_dump(exclude_unset=True)
    result = service.create_message(
        actor=current_user,
        conversation_id=conversation_id,
        data=data,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/conversations/{conversation_id}/messages
# ---------------------------------------------------------------------------


@router.get(
    "/{conversation_id}/messages", status_code=status.HTTP_200_OK
)
def list_messages(
    conversation_id: UUID,
    http_request: Request,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """List messages in a conversation with pagination. Auth required."""
    result = service.list_messages(
        actor=current_user,
        conversation_id=conversation_id,
        page=page,
        page_size=page_size,
        session=db_session,
    )
    return success(
        data=result,
        request_id=getattr(http_request.state, "request_id", None),
    )


# ---------------------------------------------------------------------------
# DELETE /api/v1/conversations/{conversation_id}/messages/{message_id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{conversation_id}/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_message(
    conversation_id: UUID,
    message_id: UUID,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
    _csrf: None = Depends(require_csrf),
) -> Response:
    """Soft-delete a message. Auth + CSRF required."""
    service.delete_message(
        actor=current_user,
        conversation_id=conversation_id,
        message_id=message_id,
        session=db_session,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
