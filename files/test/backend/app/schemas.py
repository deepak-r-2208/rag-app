"""Pydantic schemas for request/response bodies."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=6, max_length=72)


class VerifyRequest(BaseModel):
    email: EmailStr
    code: str = Field(min_length=1, max_length=12)


class ResendRequest(BaseModel):
    email: EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class DocumentOut(BaseModel):
    id: str
    name: str
    file_type: str
    char_count: int
    chunk_count: int
    created_at: datetime


class UploadResponse(BaseModel):
    documents: list[DocumentOut] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class SourceChunk(BaseModel):
    doc_name: str
    text: str
    score: float
    lexical_score: float
    vector_score: float


class ChatMessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list[SourceChunk] = Field(default_factory=list)
    confidence: str | None = None
    created_at: datetime


class ChatSessionOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(ChatSessionOut):
    messages: list[ChatMessageOut] = Field(default_factory=list)


class AskRequest(BaseModel):
    session_id: str | None = None
    question: str = Field(min_length=1, max_length=4000)


class AskResponse(BaseModel):
    session_id: str
    message: ChatMessageOut


class SettingsIn(BaseModel):
    embedding_model: str
    hybrid_weight: float = Field(ge=0.0, le=1.0)
    voice_enabled: bool


class SettingsOut(SettingsIn):
    pass
