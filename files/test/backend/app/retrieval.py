"""Hybrid search: keyword (Postgres full-text) + vector (pgvector), fused
with Reciprocal Rank Fusion (RRF) so two very differently-scaled ranking
signals combine fairly.

`hybrid_weight` (0..1) mirrors the slider in the UI: 0 leans entirely on
keyword search, 1 leans entirely on the vector model, 0.5 is balanced.
"""

import uuid
from dataclasses import dataclass

import asyncpg

RRF_K = 60
CANDIDATE_POOL = 25  # how many results to pull from each ranking system before fusing


@dataclass
class RetrievedChunk:
    chunk_id: str
    doc_name: str
    text: str
    lexical_score: float
    vector_score: float
    score: float


async def hybrid_search(
    conn: asyncpg.Connection,
    user_id: uuid.UUID,
    query: str,
    embedding_model: str,
    hybrid_weight: float,
    top_k: int,
    query_vector: list[float] | None = None,
) -> list[RetrievedChunk]:
    lexical_rows = []
    if hybrid_weight < 1:
        lexical_rows = await conn.fetch(
            """
            select c.id, c.content, d.name as doc_name,
                   ts_rank_cd(c.content_tsv, plainto_tsquery('english', $2)) as raw_score
            from chunks c
            join documents d on d.id = c.document_id
            where c.user_id = $1
              and c.content_tsv @@ plainto_tsquery('english', $2)
            order by raw_score desc
            limit $3
            """,
            user_id, query, CANDIDATE_POOL,
        )

    vector_rows = []
    if hybrid_weight > 0 and query_vector is not None:
        vector_rows = await conn.fetch(
            """
            select c.id, c.content, d.name as doc_name,
                   1 - (e.embedding <=> $2) as raw_score
            from chunk_embeddings e
            join chunks c on c.id = e.chunk_id
            join documents d on d.id = c.document_id
            where c.user_id = $1
              and e.model_name = $3
            order by e.embedding <=> $2
            limit $4
            """,
            user_id, query_vector, embedding_model, CANDIDATE_POOL,
        )

    lexical_rank = {row["id"]: i for i, row in enumerate(lexical_rows)}
    vector_rank = {row["id"]: i for i, row in enumerate(vector_rows)}
    lexical_by_id = {row["id"]: row for row in lexical_rows}
    vector_by_id = {row["id"]: row for row in vector_rows}

    all_ids = set(lexical_rank) | set(vector_rank)
    alpha = hybrid_weight
    fused: list[RetrievedChunk] = []

    for chunk_id in all_ids:
        lex_rank = lexical_rank.get(chunk_id)
        vec_rank = vector_rank.get(chunk_id)
        rrf_score = 0.0
        if lex_rank is not None:
            rrf_score += (1 - alpha) * (1.0 / (RRF_K + lex_rank + 1))
        if vec_rank is not None:
            rrf_score += alpha * (1.0 / (RRF_K + vec_rank + 1))

        row = lexical_by_id.get(chunk_id) or vector_by_id.get(chunk_id)
        fused.append(
            RetrievedChunk(
                chunk_id=str(chunk_id),
                doc_name=row["doc_name"],
                text=row["content"],
                lexical_score=float(lexical_by_id[chunk_id]["raw_score"]) if chunk_id in lexical_by_id else 0.0,
                vector_score=float(vector_by_id[chunk_id]["raw_score"]) if chunk_id in vector_by_id else 0.0,
                score=rrf_score,
            )
        )

    fused.sort(key=lambda c: c.score, reverse=True)
    if not fused:
        return []

    # Normalize fused scores to 0..1 against the best match, purely for display
    # (the focus-stack blur/opacity). Do NOT gate relevance on this — the top is
    # always 1.0 by construction, so it can't tell a real match from a weak one.
    # Grounding decisions use raw cosine/lexical scores instead (select_relevant).
    top_score = fused[0].score or 1e-9
    for c in fused:
        c.score = c.score / top_score

    return fused[:top_k]


def select_relevant(chunks: list[RetrievedChunk], min_cosine: float) -> list[RetrievedChunk]:
    """Anti-hallucination gate. Keep only chunks with a real signal: cosine
    >= min_cosine, or a literal keyword hit (lexical_score > 0 means
    plainto_tsquery actually matched).

    Runs on absolute scores, NOT the RRF-normalized score, so an off-topic
    question whose nearest neighbours are all weak (cosine ~0.15) yields [] and
    the caller refuses to answer instead of feeding the model junk context.
    """
    return [c for c in chunks if c.vector_score >= min_cosine or c.lexical_score > 0.0]


def grounding_confidence(chunks: list[RetrievedChunk]) -> str:
    """Confidence label from the strongest raw cosine similarity in the kept set.
    Pure keyword matches (no vector signal) count as medium — exact term hits
    are high-precision even at cosine 0."""
    best = max((c.vector_score for c in chunks), default=0.0)
    if best >= 0.70:
        return "high"
    if best >= 0.50:
        return "medium"
    if best > 0.0:
        return "low"
    return "medium"
