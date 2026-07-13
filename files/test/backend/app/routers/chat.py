"""Chat session history plus the core ask-a-question flow.

The /ask endpoint is where features #4 (no hallucination), #8 (hybrid
search) and #9 (chat history) meet: it runs hybrid retrieval, refuses to
call the model at all if nothing relevant was found, otherwise asks Claude
with a context-only prompt, then persists both the question and the
grounded answer (with its sources) to the session.
"""

import json

from fastapi import APIRouter, Depends, HTTPException

from app.llm_client import ask_llm
from app.config import get_settings
from app.db import get_pool
from app.embeddings import DEFAULT_MODEL
from app.retrieval import hybrid_search
from app.schemas import (
    AskRequest, AskResponse, ChatMessageOut, ChatSessionDetail, ChatSessionOut, SourceChunk,
)
from app.security import CurrentUser, get_current_user
from app.utils import parse_uuid

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/sessions", response_model=list[ChatSessionOut])
async def list_sessions(user: CurrentUser = Depends(get_current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "select id, title, created_at, updated_at from chat_sessions where user_id = $1 order by updated_at desc",
            parse_uuid(user.id, "user id"),
        )
    return [ChatSessionOut(id=str(r["id"]), title=r["title"], created_at=r["created_at"], updated_at=r["updated_at"]) for r in rows]


@router.post("/sessions", response_model=ChatSessionOut)
async def create_session(user: CurrentUser = Depends(get_current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "insert into chat_sessions (user_id) values ($1) returning id, title, created_at, updated_at",
            parse_uuid(user.id, "user id"),
        )
    return ChatSessionOut(id=str(row["id"]), title=row["title"], created_at=row["created_at"], updated_at=row["updated_at"])


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_session(session_id: str, user: CurrentUser = Depends(get_current_user)):
    session_uuid = parse_uuid(session_id, "session id")
    pool = get_pool()
    async with pool.acquire() as conn:
        session_row = await conn.fetchrow(
            "select id, title, created_at, updated_at from chat_sessions where id = $1 and user_id = $2",
            session_uuid, parse_uuid(user.id, "user id"),
        )
        if session_row is None:
            raise HTTPException(status_code=404, detail="Session not found")
        message_rows = await conn.fetch(
            "select id, role, content, sources, confidence, created_at from chat_messages where session_id = $1 order by created_at asc",
            session_uuid,
        )
    return ChatSessionDetail(
        id=str(session_row["id"]), title=session_row["title"],
        created_at=session_row["created_at"], updated_at=session_row["updated_at"],
        messages=[_row_to_message(r) for r in message_rows],
    )


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(session_id: str, user: CurrentUser = Depends(get_current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "delete from chat_sessions where id = $1 and user_id = $2",
            parse_uuid(session_id, "session id"), parse_uuid(user.id, "user id"),
        )


@router.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest, user: CurrentUser = Depends(get_current_user)):
    settings = get_settings()
    pool = get_pool()
    user_uuid = parse_uuid(user.id, "user id")

    async with pool.acquire() as conn:
        if body.session_id is None:
            row = await conn.fetchrow(
                "insert into chat_sessions (user_id, title) values ($1, $2) returning id",
                user_uuid, body.question[:48],
            )
            session_uuid = row["id"]
        else:
            session_uuid = parse_uuid(body.session_id, "session id")
            owns = await conn.fetchval(
                "select 1 from chat_sessions where id = $1 and user_id = $2", session_uuid, user_uuid
            )
            if not owns:
                raise HTTPException(status_code=404, detail="Session not found")

        user_settings = await conn.fetchrow(
            "select embedding_model, hybrid_weight from user_settings where user_id = $1", user_uuid
        )
        embedding_model = user_settings["embedding_model"] if user_settings else DEFAULT_MODEL
        hybrid_weight = user_settings["hybrid_weight"] if user_settings else 0.5

        has_documents = await conn.fetchval("select 1 from documents where user_id = $1 limit 1", user_uuid)

        await conn.execute(
            "insert into chat_messages (session_id, role, content) values ($1, 'user', $2)",
            session_uuid, body.question,
        )

        if not has_documents:
            answer, sources, confidence = (
                "You haven't added any documents yet. Upload files, then ask again.",
                [], "none",
            )
        else:
            ranked = await hybrid_search(
                conn, user_uuid, body.question, embedding_model, hybrid_weight, settings.top_k
            )
            relevant = [c for c in ranked if c.score >= settings.min_relevance_score]

            if not relevant:
                answer, sources, confidence = (
                    "Your uploaded documents don't appear to contain information about that, "
                    "so I won't guess. Try rephrasing, or add a document that covers this topic.",
                    [], "none",
                )
            else:
                history_rows = await conn.fetch(
                    "select role, content from chat_messages where session_id = $1 order by created_at asc",
                    session_uuid,
                )
                history = [{"role": r["role"], "content": r["content"]} for r in history_rows[:-1]][-8:]

                answer = await ask_llm(relevant, body.question, history)
                sources = relevant
                top = relevant[0].score
                confidence = "high" if top > 0.75 else "medium" if top > 0.4 else "low"

        sources_json = json.dumps(
            [
                {
                    "doc_name": c.doc_name, "text": c.text, "score": c.score,
                    "lexical_score": c.lexical_score, "vector_score": c.vector_score,
                }
                for c in sources
            ]
        )
        message_row = await conn.fetchrow(
            """
            insert into chat_messages (session_id, role, content, sources, confidence)
            values ($1, 'assistant', $2, $3::jsonb, $4)
            returning id, role, content, sources, confidence, created_at
            """,
            session_uuid, answer, sources_json, confidence,
        )
        await conn.execute("update chat_sessions set updated_at = now() where id = $1", session_uuid)

    return AskResponse(session_id=str(session_uuid), message=_row_to_message(message_row))


def _row_to_message(row) -> ChatMessageOut:
    raw_sources = row["sources"]
    if isinstance(raw_sources, str):
        raw_sources = json.loads(raw_sources) if raw_sources else []
    return ChatMessageOut(
        id=str(row["id"]), role=row["role"], content=row["content"],
        sources=[SourceChunk(**s) for s in (raw_sources or [])],
        confidence=row["confidence"], created_at=row["created_at"],
    )
