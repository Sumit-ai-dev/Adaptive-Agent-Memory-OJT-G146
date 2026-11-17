"""
Multi-Thread Conversational Studio API Endpoints.
Provides CRUD and message persistence for multi-turn conversation threads.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ai_service.config import settings
from backend.routes.agent import shared_store
from backend.security.auth import AuthContext, get_optional_auth_context
from models.conversation import (
    Conversation,
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationMessage,
    ConversationMessageCreateRequest,
    ConversationUpdateRequest,
)

logger = logging.getLogger("backend.routes.conversations")

router = APIRouter(prefix="/conversations", tags=["Conversations"])


def _check_auth_policy(auth: Optional[AuthContext]) -> None:
    """Enforces authentication when REQUIRE_USER_AUTH setting is enabled."""
    if getattr(settings, "REQUIRE_USER_AUTH", False):
        if not auth or not auth.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
                headers={"WWW-Authenticate": "Bearer"},
            )


@router.post(
    "",
    response_model=Conversation,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation thread",
)
async def create_conversation(
    body: ConversationCreateRequest,
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> Conversation:
    """Creates a persistent multi-turn conversation thread."""
    _check_auth_policy(auth)

    user_id = auth.user_id if (auth and auth.is_authenticated) else None
    conv_id = body.id or str(uuid.uuid4())

    existing = await shared_store.get_conversation(conv_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conversation with ID '{conv_id}' already exists.",
        )

    conv = Conversation(
        id=conv_id,
        user_id=user_id,
        title=body.title or "New Conversation",
        is_pinned=body.is_pinned,
    )
    try:
        saved = await shared_store.create_conversation(conv)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conversation with ID '{conv_id}' could not be created: {exc}",
        )
    return saved


@router.get(
    "",
    response_model=ConversationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List persistent conversations",
)
async def list_conversations(
    limit: int = Query(50, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Offset position"),
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> ConversationListResponse:
    """Lists conversations scoped to the calling user with pinning support."""
    _check_auth_policy(auth)

    user_id: Optional[str] = None
    unauthenticated_only = False

    if auth and auth.is_authenticated:
        if not auth.is_admin and not auth.is_machine:
            user_id = auth.user_id
    else:
        unauthenticated_only = True

    total, items = await shared_store.list_conversations(
        user_id=user_id,
        unauthenticated_only=unauthenticated_only,
        limit=limit,
        offset=offset,
    )
    return ConversationListResponse(total=total, items=items)


@router.get(
    "/{conversation_id}",
    response_model=Conversation,
    status_code=status.HTTP_200_OK,
    summary="Get conversation details by ID",
)
async def get_conversation(
    conversation_id: str,
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> Conversation:
    """Retrieves conversation metadata by ID ensuring tenant isolation."""
    _check_auth_policy(auth)

    conv = await shared_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    # Multi-tenant isolation check
    if conv.user_id:
        if not auth or not auth.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )
        if not auth.is_admin and not auth.is_machine and auth.user_id != conv.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )

    return conv


@router.patch(
    "/{conversation_id}",
    response_model=Conversation,
    status_code=status.HTTP_200_OK,
    summary="Update conversation metadata",
)
async def update_conversation(
    conversation_id: str,
    body: ConversationUpdateRequest,
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> Conversation:
    """Updates conversation title or pin state."""
    _check_auth_policy(auth)

    conv = await shared_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    if conv.user_id:
        if not auth or not auth.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )
        if not auth.is_admin and not auth.is_machine and auth.user_id != conv.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )

    updated = await shared_store.update_conversation(
        conv_id=conversation_id,
        user_id=conv.user_id,
        title=body.title,
        is_pinned=body.is_pinned,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )
    return updated


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete conversation and associated messages",
)
async def delete_conversation(
    conversation_id: str,
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> Dict[str, Any]:
    """Deletes conversation and its message turns."""
    _check_auth_policy(auth)

    conv = await shared_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    if conv.user_id:
        if not auth or not auth.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )
        if not auth.is_admin and not auth.is_machine and auth.user_id != conv.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )

    deleted = await shared_store.delete_conversation(conversation_id, user_id=conv.user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )
    return {"status": "deleted", "id": conversation_id}


@router.get(
    "/{conversation_id}/messages",
    response_model=List[ConversationMessage],
    status_code=status.HTTP_200_OK,
    summary="Get chronological message turns in a conversation",
)
async def get_conversation_messages(
    conversation_id: str,
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> List[ConversationMessage]:
    """Retrieves all message turns for a conversation ordered chronologically."""
    _check_auth_policy(auth)

    conv = await shared_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    if conv.user_id:
        if not auth or not auth.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )
        if not auth.is_admin and not auth.is_machine and auth.user_id != conv.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )

    messages = await shared_store.get_conversation_messages(conversation_id, user_id=conv.user_id)
    return messages


@router.post(
    "/{conversation_id}/messages",
    response_model=ConversationMessage,
    status_code=status.HTTP_201_CREATED,
    summary="Append a new message turn to conversation",
)
async def add_conversation_message(
    conversation_id: str,
    body: ConversationMessageCreateRequest,
    auth: Optional[AuthContext] = Depends(get_optional_auth_context),
) -> ConversationMessage:
    """Appends a message turn and updates the conversation timestamp."""
    _check_auth_policy(auth)

    conv = await shared_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found.",
        )

    if conv.user_id:
        if not auth or not auth.is_authenticated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )
        if not auth.is_admin and not auth.is_machine and auth.user_id != conv.user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )

    msg = ConversationMessage(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        user_id=conv.user_id,
        role=body.role,
        content=body.content,
    )
    saved = await shared_store.add_conversation_message(msg)
    return saved
