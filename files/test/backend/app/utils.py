"""Small shared helpers."""

import uuid

from fastapi import HTTPException


def parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}: {value!r}") from exc
