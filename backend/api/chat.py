"""AEGIS AI — Chat and Streaming Dialogue Endpoints
Provides conversation management and Server-Sent Events (SSE) streaming chat.
"""

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db
from backend.schemas.chat import (
    ChatMessageListResponse,
    ChatMessageResponse,
    ChatStreamRequest,
    ConversationCreateRequest,
    ConversationListResponse,
    ConversationResponse,
)
from backend.security.dependencies import CurrentUser, get_current_user
from backend.services.chat_service import ChatService

chat_router = APIRouter(prefix="/chat", tags=["Chat & Dialogue"])


@chat_router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation session",
)
async def create_conversation(
    payload: ConversationCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    conv = await ChatService.create_conversation(
        db=db,
        user_id=current_user.user_id,
        organization_id=current_user.organization_id,
        title=payload.title,
    )
    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        organization_id=conv.organization_id,
        title=conv.title,
        status=conv.status,
        message_count=0,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@chat_router.get(
    "/conversations",
    response_model=ConversationListResponse,
    summary="List conversations for the current tenant",
)
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationListResponse:
    conversations, total = await ChatService.list_conversations(
        db=db,
        organization_id=current_user.organization_id,
        limit=limit,
        offset=offset,
    )
    return ConversationListResponse(
        conversations=[ConversationResponse(**c) for c in conversations],
        total=total,
    )


@chat_router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationResponse,
    summary="Get conversation details",
)
async def get_conversation(
    conversation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    conv = await ChatService.get_conversation(
        db=db,
        conversation_id=conversation_id,
        organization_id=current_user.organization_id,
    )
    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        organization_id=conv.organization_id,
        title=conv.title,
        status=conv.status,
        message_count=len(conv.messages),
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@chat_router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation and its messages",
)
async def delete_conversation(
    conversation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await ChatService.delete_conversation(
        db=db,
        conversation_id=conversation_id,
        organization_id=current_user.organization_id,
    )


@chat_router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageListResponse,
    summary="Get message history for a conversation",
)
async def get_conversation_messages(
    conversation_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatMessageListResponse:
    messages = await ChatService.get_conversation_messages(
        db=db,
        conversation_id=conversation_id,
        organization_id=current_user.organization_id,
    )
    return ChatMessageListResponse(
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
        total=len(messages),
    )


@chat_router.post(
    "/stream",
    summary="Stream AI chat response via Server-Sent Events (SSE)",
)
async def stream_chat(
    payload: ChatStreamRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    stream_generator = ChatService.stream_chat_response(
        db=db,
        user_id=current_user.user_id,
        organization_id=current_user.organization_id,
        message=payload.message,
        conversation_id=payload.conversation_id,
        knowledge_base_id=payload.knowledge_base_id,
        model_name=payload.model,
        temperature=payload.temperature,
    )

    return StreamingResponse(
        stream_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
