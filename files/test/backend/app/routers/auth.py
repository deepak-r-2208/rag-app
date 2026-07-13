"""Signup, email-code verification, and login.

There's no SMTP/email service wired up by default, so verification codes
are returned directly in the API response (and shown in the frontend UI)
instead of being emailed. That keeps the whole stack free and dependency-
free for local/learning use. If you want real emails later, generate the
code here as usual and add a call to any mail provider before returning
the response — everything else in this file stays the same.
"""

import random
import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.db import get_pool
from app.schemas import LoginRequest, ResendRequest, SignupRequest, VerifyRequest
from app.security import CurrentUser, create_access_token, get_current_user, hash_password, verify_password
from app.utils import parse_uuid

router = APIRouter(prefix="/auth", tags=["auth"])


def _gen_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def _user_out(row) -> dict:
    return {"id": str(row["id"]), "name": row["name"], "email": row["email"]}


@router.post("/signup")
async def signup(body: SignupRequest):
    pool = get_pool()
    email = body.email.lower()
    async with pool.acquire() as conn:
        existing = await conn.fetchval("select 1 from users where email = $1", email)
        if existing:
            raise HTTPException(status_code=400, detail="An account already exists for that email.")
        code = _gen_code()
        await conn.execute(
            """
            insert into users (id, name, email, password_hash, verified, verification_code)
            values ($1, $2, $3, $4, false, $5)
            """,
            uuid.uuid4(), body.name, email, hash_password(body.password), code,
        )
    return {
        "message": "Account created. Enter the code to verify.",
        "verification_code": code,
        "dev_note": "No email service is configured, so the code is returned here instead of "
                    "being emailed. See README if you want to wire up a real mail provider.",
    }


@router.post("/resend")
async def resend(body: ResendRequest):
    pool = get_pool()
    email = body.email.lower()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("select id from users where email = $1", email)
        if not user:
            raise HTTPException(status_code=404, detail="No account with that email.")
        code = _gen_code()
        await conn.execute("update users set verification_code = $1 where id = $2", code, user["id"])
    return {"verification_code": code}


@router.post("/verify")
async def verify(body: VerifyRequest):
    pool = get_pool()
    email = body.email.lower()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "select id, name, email, verification_code from users where email = $1", email
        )
        if not user:
            raise HTTPException(status_code=404, detail="No account with that email.")
        if not user["verification_code"] or user["verification_code"] != body.code:
            raise HTTPException(status_code=400, detail="That code doesn't match.")
        await conn.execute(
            "update users set verified = true, verification_code = null where id = $1", user["id"]
        )
    token = create_access_token(str(user["id"]), user["email"])
    return {"access_token": token, "user": _user_out(user)}


@router.post("/login")
async def login(body: LoginRequest):
    pool = get_pool()
    email = body.email.lower()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "select id, name, email, password_hash, verified, verification_code from users where email = $1",
            email,
        )
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    if not user["verified"]:
        # 200, not an error — the frontend routes to the verify pane and
        # shows this code, same as it does right after signup.
        return {"needs_verification": True, "email": user["email"], "verification_code": user["verification_code"]}

    token = create_access_token(str(user["id"]), user["email"])
    return {"access_token": token, "user": _user_out(user), "needs_verification": False}


@router.get("/me")
async def me(user: CurrentUser = Depends(get_current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("select id, name, email from users where id = $1", parse_uuid(user.id, "user id"))
    if not row:
        raise HTTPException(status_code=404, detail="User not found.")
    return _user_out(row)
