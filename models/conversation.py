"""
Pydantic Data Models for Multi-Thread Conversational Studio (Pillar 3).
Provides typed schemas for Conversation threads, Messages, and CRUD operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Conversation(BaseModel):
    """Represents a persistent multi-turn chat conversation thread."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str = Field(..., description="Unique conversation session ID")
    user_id: Optional[str] = Field(default=None, description="Tenant user ID owner")
    title: str = Field(default="New Conversation", description="Conversation topic title")
    is_pinned: bool = Field(default=False, description="Whether pinned to the top of the sidebar")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message_count: int = Field(default=0, description="Total message turn count")


class ConversationCreateRequest(BaseModel):
    """Payload to initialize a new conversation thread."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: Optional[str] = Field(default=None, description="Client-specified session ID")
    title: Optional[str] = Field(default=None, description="Initial conversation title")
    is_pinned: bool = Field(default=False, description="Initial pinned state")


class ConversationUpdateRequest(BaseModel):
    """Payload to modify conversation metadata (rename title, toggle pin)."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    title: Optional[str] = Field(default=None, min_length=1, max_length=200, description="Updated title")
    is_pinned: Optional[bool] = Field(default=None, description="Updated pinned state")


class ConversationMessage(BaseModel):
    """Represents an individual conversational message turn."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str = Field(..., description="Unique message ID")
    conversation_id: str = Field(..., description="Parent conversation ID")
    user_id: Optional[str] = Field(default=None, description="Tenant user ID")
    role: str = Field(..., description="Message role: user, assistant, or system")
    content: str = Field(..., min_length=1, description="Message content")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationMessageCreateRequest(BaseModel):
    """Payload to append a message to a conversation."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    role: str = Field(default="user", description="Message role: user or assistant")
    content: str = Field(..., min_length=1, description="Message content")


class ConversationListResponse(BaseModel):
    """Paginated response containing conversation summaries."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    total: int
    items: List[Conversation]
