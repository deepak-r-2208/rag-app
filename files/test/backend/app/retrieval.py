"""Hybrid search: keyword (Postgres full-text) + vector (pgvector), fused
with Reciprocal Rank Fusion (RRF) so two very differently-scaled ranking
signals combine fairly.

`hybrid_weight` (0..1) mirrors the slider in the UI: 0 leans entirely on
keyword search, 1 leans entirely on the vector model, 0.5 is balanced.
"""

import uuid
from dataclasses import dataclass

import asyncpg

from app.embeddings import embed_query

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
) -> list[RetrievedChunk]:
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

    query_vector = await embed_query(query, embedding_model)
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

    # Normalize fused scores to 0..1 against the best match so the UI/threshold
    # logic doesn't depend on RRF's small absolute magnitudes.
    top_score = fused[0].score or 1e-9
    for c in fused:
        c.score = c.score / top_score

    return fused[:top_k]
