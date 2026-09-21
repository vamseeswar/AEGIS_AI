"""AEGIS AI — Chat Service & Streaming Dialogue Engine
Handles conversation lifecycle, RAG grounding, multi-turn history, and SSE token streaming.
"""

import json
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.ai.providers import get_llm_provider
from backend.core.errors import ResourceNotFoundError, TenantIsolationError
from backend.models.chat import Conversation, Message
from backend.rag.citation import extract_and_verify_citations, format_context_with_citations
from backend.rag.retriever import retrieve_relevant_chunks


class ChatService:
    @staticmethod
    async def create_conversation(
        db: AsyncSession,
        user_id: str,
        organization_id: str,
        title: str = "New Conversation",
    ) -> Conversation:
        conversation = Conversation(
            user_id=user_id,
            organization_id=organization_id,
            title=title.strip() or "New Conversation",
            status="active",
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def list_conversations(
        db: AsyncSession,
        organization_id: str,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        count_stmt = (
            select(func.count(Conversation.id))
            .where(Conversation.organization_id == organization_id)
        )
        if user_id:
            count_stmt = count_stmt.where(Conversation.user_id == user_id)

        total_res = await db.execute(count_stmt)
        total = total_res.scalar_one()

        stmt = (
            select(
                Conversation,
                func.count(Message.id).label("message_count"),
            )
            .outerjoin(Message, Message.conversation_id == Conversation.id)
            .where(Conversation.organization_id == organization_id)
            .group_by(Conversation.id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .offset(offset)
        )

        if user_id:
            stmt = stmt.where(Conversation.user_id == user_id)

        result = await db.execute(stmt)
        rows = result.all()

        conversations = []
        for conv, msg_count in rows:
            conversations.append(
                {
                    "id": conv.id,
                    "user_id": conv.user_id,
                    "organization_id": conv.organization_id,
                    "title": conv.title,
                    "status": conv.status,
                    "message_count": msg_count,
                    "created_at": conv.created_at,
                    "updated_at": conv.updated_at,
                }
            )

        return conversations, total

    @staticmethod
    async def get_conversation(
        db: AsyncSession,
        conversation_id: str,
        organization_id: str,
    ) -> Conversation:
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.messages))
        )
        result = await db.execute(stmt)
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise ResourceNotFoundError("Conversation", conversation_id)

        if conversation.organization_id != organization_id:
            raise TenantIsolationError("Access to cross-tenant conversation denied.")

        return conversation

    @staticmethod
    async def delete_conversation(
        db: AsyncSession,
        conversation_id: str,
        organization_id: str,
    ) -> None:
        conversation = await ChatService.get_conversation(db, conversation_id, organization_id)
        await db.delete(conversation)
        await db.commit()

    @staticmethod
    async def get_conversation_messages(
        db: AsyncSession,
        conversation_id: str,
        organization_id: str,
    ) -> list[Message]:
        await ChatService.get_conversation(db, conversation_id, organization_id)

        stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation_id,
                Message.organization_id == organization_id,
            )
            .order_by(Message.created_at.asc())
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def stream_chat_response(
        db: AsyncSession,
        user_id: str,
        organization_id: str,
        message: str,
        conversation_id: str | None = None,
        knowledge_base_id: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.2,
    ) -> AsyncGenerator[str, None]:
        """Orchestrates RAG retrieval, token streaming, citation extraction, and DB persistence.
        Yields Server-Sent Events (SSE) formatted as: 'data: {...}\\n\\n'.
        """
        # 1. Resolve or create conversation
        if conversation_id:
            conversation = await ChatService.get_conversation(db, conversation_id, organization_id)
        else:
            conversation = await ChatService.create_conversation(
                db=db,
                user_id=user_id,
                organization_id=organization_id,
                title="New Conversation",
            )

        # 2. Persist user message
        user_msg = Message(
            conversation_id=conversation.id,
            user_id=user_id,
            organization_id=organization_id,
            role="user",
            content=message.strip(),
        )
        db.add(user_msg)
        await db.commit()

        meta_event = {
            "type": "metadata",
            "conversation_id": conversation.id,
            "conversation_title": conversation.title,
            "user_message_id": user_msg.id,
        }
        yield f"data: {json.dumps(meta_event)}\n\n"

        # 3. Retrieve relevant chunks from vector store (increased top_k for better coverage)
        chunks = await retrieve_relevant_chunks(
            query=message,
            organization_id=organization_id,
            db=db,
            knowledge_base_id=knowledge_base_id,
            top_k=8,
            score_threshold=0.0,
        )

        context_block = format_context_with_citations(chunks) if chunks else ""

        # 4. Build a precise, task-focused system prompt
        system_instruction = (
            "You are AEGIS AI, an advanced enterprise document intelligence assistant. "
            "Your job is to answer the user's question accurately and specifically using ONLY "
            "the information present in the provided documents.\n\n"
            "Rules:\n"
            "- Extract exact facts, names, numbers, dates, and details directly from the document text.\n"
            "- Do NOT paraphrase vaguely — quote or closely reference specific sections.\n"
            "- If the answer to the question is present in the document, provide it completely.\n"
            "- If a specific piece of information (e.g., contact details, skills, dates) is asked, "
            "find and list ALL instances of that information from the documents.\n"
            "- Cite each fact using its citation token like [doc_id:p.N].\n"
            "- If the requested information is truly not present in any document, say so clearly.\n"
            "- Do NOT fabricate information or make assumptions beyond what the documents state.\n"
        )

        if chunks:
            system_instruction += (
                f"\nThe following document excerpts have been retrieved for this query:\n\n"
                f"{context_block}\n\n"
                "Answer the user's question based strictly on the above document content."
            )
        else:
            system_instruction += (
                "\nNo relevant documents were found in the knowledge base for this query. "
                "Inform the user that no matching documents are available and suggest they "
                "upload relevant files via the Documents page."
            )

        # 5. Retrieve recent conversation history (up to last 10 messages)
        history_stmt = (
            select(Message)
            .where(
                Message.conversation_id == conversation.id,
                Message.organization_id == organization_id,
            )
            .order_by(Message.created_at.asc())
            .limit(10)
        )
        history_res = await db.execute(history_stmt)
        past_msgs = history_res.scalars().all()

        llm_messages: list[dict[str, str]] = [{"role": "system", "content": system_instruction}]
        for m in past_msgs:
            llm_messages.append({"role": m.role, "content": m.content})

        # 6. Stream LLM tokens
        provider = get_llm_provider(model_name=model_name)
        accumulated_text: list[str] = []

        try:
            async for token in provider.generate_stream(
                messages=llm_messages,
                temperature=temperature,
            ):
                accumulated_text.append(token)
                token_event = {"type": "token", "content": token}
                yield f"data: {json.dumps(token_event)}\n\n"
        except Exception as stream_err:
            # Log the error and emit an error token event
            error_msg = f"⚠️ AI stream error: {stream_err}. Attempting fallback..."
            token_event = {"type": "token", "content": error_msg}
            yield f"data: {json.dumps(token_event)}\n\n"
            accumulated_text.append(error_msg)

            # Resilient fallback to deterministic mock provider
            try:
                fallback_provider = get_llm_provider(provider_type="mock", model_name="mock-aegis-core")
                async for token in fallback_provider.generate_stream(
                    messages=llm_messages,
                    temperature=temperature,
                ):
                    accumulated_text.append(token)
                    token_event = {"type": "token", "content": token}
                    yield f"data: {json.dumps(token_event)}\n\n"
            except Exception:
                pass

        full_response = "".join(accumulated_text).strip()

        # 7. Extract and verify citations against retrieved chunks
        verified_citations, unverified_tokens = extract_and_verify_citations(
            llm_output=full_response,
            retrieved_chunks=chunks,
        )

        citations_payload = [
            {
                "citation_token": c.citation_token,
                "document_id": c.document_id,
                "document_title": c.document_title,
                "filename": c.filename,
                "page_number": c.page_number,
                "excerpt": c.excerpt,
                "score": c.score,
            }
            for c in verified_citations
        ]

        if citations_payload:
            citations_event = {"type": "citations", "citations": citations_payload}
            yield f"data: {json.dumps(citations_event)}\n\n"

        # 8. Persist assistant message
        assistant_msg = Message(
            conversation_id=conversation.id,
            organization_id=organization_id,
            role="assistant",
            content=full_response,
            citations_json=citations_payload if citations_payload else None,
            metadata_json={"model": provider.model_name},
        )
        db.add(assistant_msg)

        # 9. Auto-generate conversation title if still default
        if conversation.title == "New Conversation" and message:
            clean_title = message.strip().replace("\n", " ")
            if len(clean_title) > 40:
                clean_title = clean_title[:37] + "..."
            conversation.title = clean_title

        await db.commit()

        done_event = {
            "type": "done",
            "conversation_id": conversation.id,
            "assistant_message_id": assistant_msg.id,
        }
        yield f"data: {json.dumps(done_event)}\n\n"
