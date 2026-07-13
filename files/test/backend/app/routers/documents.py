"""Document ingestion endpoints: upload (parse -> chunk -> embed), list, delete."""

from fastapi import APIRouter, Depends, File, UploadFile

from app import chunking, parsing
from app.db import get_pool
from app.embeddings import embed_all_models
from app.schemas import DocumentOut, UploadResponse
from app.security import CurrentUser, get_current_user
from app.utils import parse_uuid

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", response_model=list[DocumentOut])
async def list_documents(user: CurrentUser = Depends(get_current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select id, name, file_type, char_count, chunk_count, created_at
            from documents where user_id = $1
            order by created_at desc
            """,
            parse_uuid(user.id, "user id"),
        )
    return [
        DocumentOut(
            id=str(r["id"]), name=r["name"], file_type=r["file_type"],
            char_count=r["char_count"], chunk_count=r["chunk_count"], created_at=r["created_at"],
        )
        for r in rows
    ]


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: str, user: CurrentUser = Depends(get_current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "delete from documents where id = $1 and user_id = $2",
            parse_uuid(document_id, "document id"), parse_uuid(user.id, "user id"),
        )


@router.post("/upload", response_model=UploadResponse)
async def upload_documents(
    files: list[UploadFile] = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    pool = get_pool()
    response = UploadResponse()
    user_uuid = parse_uuid(user.id, "user id")

    for file in files:
        try:
            text = await parsing.extract_text(file)
            if not text.strip():
                response.errors.append(f"{file.filename}: no extractable text found")
                continue

            pieces = chunking.chunk_text(text)
            if not pieces:
                response.errors.append(f"{file.filename}: produced no chunks")
                continue

            ext = parsing.extension_of(file.filename or "")
            texts = [p.text for p in pieces]

            # Compute embeddings for every registered model up front (in
            # parallel) so the user can switch models later without
            # re-uploading documents.
            model_vectors = await embed_all_models(texts)

            async with pool.acquire() as conn:
                async with conn.transaction():
                    doc_row = await conn.fetchrow(
                        """
                        insert into documents (user_id, name, file_type, char_count, chunk_count)
                        values ($1, $2, $3, $4, $5)
                        returning id, name, file_type, char_count, chunk_count, created_at
                        """,
                        user_uuid, file.filename, ext, len(text), len(pieces),
                    )
                    document_id = doc_row["id"]

                    chunk_ids: list = []
                    for piece in pieces:
                        row = await conn.fetchrow(
                            """
                            insert into chunks (document_id, user_id, chunk_index, content)
                            values ($1, $2, $3, $4)
                            returning id
                            """,
                            document_id, user_uuid, piece.index, piece.text,
                        )
                        chunk_ids.append(row["id"])

                    for model_name, vectors in model_vectors.items():
                        await conn.executemany(
                            """
                            insert into chunk_embeddings (chunk_id, model_name, embedding)
                            values ($1, $2, $3)
                            """,
                            [(cid, model_name, vec) for cid, vec in zip(chunk_ids, vectors)],
                        )

            response.documents.append(
                DocumentOut(
                    id=str(doc_row["id"]), name=doc_row["name"], file_type=doc_row["file_type"],
                    char_count=doc_row["char_count"], chunk_count=doc_row["chunk_count"],
                    created_at=doc_row["created_at"],
                )
            )
        except parsing.UnsupportedFormatError as exc:
            response.errors.append(f"{file.filename}: {exc}")
        except Exception as exc:  # noqa: BLE001 — surface any parser/OCR failure to the user
            response.errors.append(f"{file.filename}: {exc}")

    return response
