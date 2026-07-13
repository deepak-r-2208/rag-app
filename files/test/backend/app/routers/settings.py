"""Get/update the current user's retrieval and voice preferences."""

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_pool
from app.embeddings import DEFAULT_MODEL, available_models
from app.schemas import SettingsIn, SettingsOut
from app.security import CurrentUser, get_current_user
from app.utils import parse_uuid

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=SettingsOut)
async def get_settings_endpoint(user: CurrentUser = Depends(get_current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select embedding_model, hybrid_weight, voice_enabled from user_settings where user_id = $1",
            parse_uuid(user.id, "user id"),
        )
    if row is None:
        return SettingsOut(embedding_model=DEFAULT_MODEL, hybrid_weight=0.5, voice_enabled=True)
    return SettingsOut(**dict(row))


@router.put("", response_model=SettingsOut)
async def update_settings(body: SettingsIn, user: CurrentUser = Depends(get_current_user)):
    if body.embedding_model not in available_models():
        raise HTTPException(status_code=400, detail=f"Unknown embedding model: {body.embedding_model}")

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            insert into user_settings (user_id, embedding_model, hybrid_weight, voice_enabled)
            values ($1, $2, $3, $4)
            on conflict (user_id) do update
              set embedding_model = excluded.embedding_model,
                  hybrid_weight = excluded.hybrid_weight,
                  voice_enabled = excluded.voice_enabled
            """,
            parse_uuid(user.id, "user id"), body.embedding_model, body.hybrid_weight, body.voice_enabled,
        )
    return SettingsOut(**body.model_dump())
