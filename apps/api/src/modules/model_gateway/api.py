"""Internal Model Gateway API endpoints.

These endpoints are called by internal services (Agent Service, Scene
Service) — not by end users. They are registered under /internal/v1/model/*.

Aligned with API_CONTRACT EP-MODEL-058/059/060:
- POST /internal/v1/model/chat
- POST /internal/v1/model/embedding
- GET  /internal/v1/model/health

Privacy: request/response bodies are never logged. Only hashes and
metadata are persisted to AgentRun.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ...dependencies import get_db_session
from ...schemas.envelope import success
from .schemas import (
    ChatRequest,
    EmbeddingRequest,
)
from .service import get_model_gateway_service

router = APIRouter(prefix="/internal/v1/model", tags=["model-gateway"])


@router.post("/chat")
async def model_chat(
    request: Request,
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Internal chat completion endpoint (EP-MODEL-058).

    Called by Agent/Scene services. Routes through the privacy-aware
    gateway, validates structured output, and records AgentRun metadata.
    """
    body = await request.json()
    chat_request = ChatRequest(**body)
    service = get_model_gateway_service()
    response = service.chat(chat_request)
    return success(
        data=response.model_dump(mode="json"),
        request_id=getattr(request.state, "correlation_id", None),
    )


@router.post("/embedding")
async def model_embedding(
    request: Request,
    db_session: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Internal embedding endpoint (EP-MODEL-059)."""
    body = await request.json()
    emb_request = EmbeddingRequest(**body)
    service = get_model_gateway_service()
    response = service.embedding(emb_request)
    return success(
        data=response.model_dump(mode="json"),
        request_id=getattr(request.state, "correlation_id", None),
    )


@router.get("/health")
async def model_health(
    request: Request,
) -> dict[str, Any]:
    """Internal model health endpoint (EP-MODEL-060)."""
    service = get_model_gateway_service()
    data = service.health()
    return success(
        data=data,
        request_id=getattr(request.state, "correlation_id", None),
    )
