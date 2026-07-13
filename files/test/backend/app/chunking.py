"""Recursive, structure-aware chunking with sliding-window overlap.

Splits on paragraph boundaries first (so related sentences stay together),
falling back to sentence-level splitting for paragraphs longer than the
target size. Each chunk after the first is prefixed with a tail of the
previous chunk so retrieval doesn't lose context at a boundary.
"""

import re
from dataclasses import dataclass

# Split *after* a sentence-ending punctuation mark followed by whitespace.
# Unlike a "match a sentence" pattern, a split can never silently drop
# characters that don't happen to end in punctuation — worst case it
# returns the whole paragraph as one piece, which the hard-split fallback
# below then bounds in size.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Chunk:
    index: int
    text: str


def _split_sentences(paragraph: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(paragraph) if p.strip()]
    return parts or [paragraph]


def _hard_split(text: str, size: int) -> list[str]:
    """Last-resort character split for a single run with no punctuation at all."""
    pieces = [text[i:i + size] for i in range(0, len(text), size)]
    return pieces or [text]


def chunk_text(text: str, target_size: int = 700, overlap: int = 120) -> list[Chunk]:
    clean = re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n")).strip()
    if not clean:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", clean) if p.strip()]
    raw_chunks: list[str] = []
    buffer = ""

    def flush():
        nonlocal buffer
        if buffer.strip():
            raw_chunks.append(buffer.strip())
        buffer = ""

    for para in paragraphs:
        if len(buffer) + 2 + len(para) <= target_size:
            buffer = f"{buffer}\n\n{para}" if buffer else para
            continue
        if len(para) <= target_size:
            flush()
            buffer = para
            continue
        for sentence in _split_sentences(para):
            # Guard against a single "sentence" (no punctuation at all)
            # that's still longer than the target size on its own.
            pieces = [sentence] if len(sentence) <= target_size * 1.5 else _hard_split(sentence, target_size)
            for piece in pieces:
                if len(buffer) + 1 + len(piece) <= target_size:
                    buffer = f"{buffer} {piece}" if buffer else piece
                else:
                    flush()
                    buffer = piece
    flush()

    chunks: list[Chunk] = []
    for i, text_piece in enumerate(raw_chunks):
        if i == 0:
            chunks.append(Chunk(index=i, text=text_piece))
        else:
            tail = raw_chunks[i - 1][-overlap:]
            chunks.append(Chunk(index=i, text=f"{tail} \u2026 {text_piece}"))
    return chunks
