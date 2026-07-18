"""Calls a local Ollama chat model with a strict, context-only grounding prompt.

This is the anti-hallucination layer (feature #4): the model only ever sees
the chunks retrieval decided were relevant, is told not to use outside
knowledge, and is asked to cite its source. The caller (routers/chat.py)
additionally refuses to call this at all when retrieval found nothing
relevant — the strongest guarantee is simply not asking the model to
answer unsupported questions.

Runs entirely on your own machine via Ollama — no API key, no per-call
cost. Pull a chat model once, e.g.:

    ollama pull llama3.1:8b        # good default, needs ~8GB RAM
    ollama pull llama3.2:3b        # lighter alternative, ~4GB RAM

Local models are noticeably less reliable than a frontier hosted model at
following strict grounding instructions — expect somewhat more slip-ups
on the "don't guess" rule than you'd see from a larger hosted model.
"""

import httpx

from app.config import get_settings
from app.retrieval import RetrievedChunk


def _build_system_prompt(chunks: list[RetrievedChunk]) -> str:
    context = "\n\n".join(
        f"[{i + 1}] (source: {c.doc_name})\n{c.text}" for i, c in enumerate(chunks)
    )
    return (
        "You are the answer engine inside RAGnify Media, a retrieval-augmented app "
        "over the user's own documents.\n"
        "Answer ONLY using the CONTEXT below. Never use outside knowledge, even if you "
        "know the answer.\n"
        "If the context does not contain the answer, say plainly that the uploaded "
        "documents don't cover it — do not guess.\n"
        "When you do answer, cite the source numbers you relied on, like [1] or [2].\n"
        "Keep answers concise and direct.\n\n"
        f"CONTEXT:\n{context}"
    )


async def ask_llm(
    chunks: list[RetrievedChunk],
    question: str,
    history: list[dict],
) -> str:
    settings = get_settings()
    messages = [{"role": "system", "content": _build_system_prompt(chunks)}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    async with httpx.AsyncClient(timeout=180) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/chat",
            json={
                "model": settings.ollama_chat_model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 160},
            },
        )
        resp.raise_for_status()
        data = resp.json()

    return (data.get("message") or {}).get("content", "").strip()
