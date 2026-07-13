"""Embedding models served by a local Ollama instance.

Completely free: everything runs on your own machine via Ollama, no API
key and no per-call cost. Pull the models once with:

    ollama pull all-minilm
    ollama pull nomic-embed-text

The two models intentionally have different vector widths (384 vs 768) to
give a real fast/quality tradeoff — see sql/schema.sql for how that's
handled (a dimension-agnostic `vector` column rather than a fixed size).
"""

import asyncio

import httpx

from app.config import get_settings

MODEL_REGISTRY: dict[str, str] = {
    "all-minilm": "46MB, 384-dim — fast and light",
    "nomic-embed-text": "274MB, 768-dim — stronger semantic recall",
}

DEFAULT_MODEL = "all-minilm"


def available_models() -> list[str]:
    return list(MODEL_REGISTRY.keys())


async def embed_texts(texts: list[str], model_name: str = DEFAULT_MODEL) -> list[list[float]]:
    if not texts:
        return []
    settings = get_settings()
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{settings.ollama_base_url}/api/embed",
            json={"model": model_name, "input": texts},
        )
        resp.raise_for_status()
        data = resp.json()
    return data["embeddings"]


async def embed_all_models(texts: list[str]) -> dict[str, list[list[float]]]:
    """Embed the same texts with every registered model, concurrently."""
    names = available_models()
    results = await asyncio.gather(*(embed_texts(texts, name) for name in names))
    return dict(zip(names, results))


async def embed_query(query: str, model_name: str = DEFAULT_MODEL) -> list[float]:
    vectors = await embed_texts([query], model_name)
    return vectors[0]
