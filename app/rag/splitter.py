"""Small recursive Chinese-aware character splitter with overlap."""

import re

from app.rag.models import KnowledgeChunk, PageDocument

_SEPARATORS = ("\n\n", "\n", "。", "！", "？", "；", "，", "")


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _recursive_units(text: str, chunk_size: int, separators: tuple[str, ...]) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    separator = next((item for item in separators if item and item in text), "")
    if not separator:
        return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]

    next_separators = separators[separators.index(separator) + 1 :]
    pieces = re.split(f"(?<={re.escape(separator)})", text)
    units: list[str] = []
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        units.extend(_recursive_units(piece, chunk_size, next_separators))
    return units


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text by semantic punctuation first and carry a bounded overlap."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")

    normalized = _normalize_text(text)
    if not normalized:
        return []
    units = _recursive_units(normalized, chunk_size, _SEPARATORS)

    chunks: list[str] = []
    current = ""
    for unit in units:
        if not current:
            current = unit
            continue
        if len(current) + len(unit) <= chunk_size:
            current += unit
            continue
        chunks.append(current.strip())
        overlap = current[-chunk_overlap:] if chunk_overlap else ""
        current = (overlap + unit).strip()
        if len(current) > chunk_size:
            chunks.extend(
                current[index : index + chunk_size].strip()
                for index in range(0, len(current) - chunk_size, chunk_size - chunk_overlap)
            )
            current = current[-chunk_size:]
    if current.strip():
        chunks.append(current.strip())

    return [chunk for chunk in chunks if chunk]


def split_pages(
    pages: list[PageDocument], chunk_size: int, chunk_overlap: int
) -> list[KnowledgeChunk]:
    """Split pages while preserving stable source IDs and metadata."""
    chunks: list[KnowledgeChunk] = []
    for page in pages:
        page_chunks = split_text(page.content, chunk_size, chunk_overlap)
        stem = page.file.rsplit(".", maxsplit=1)[0]
        for index, content in enumerate(page_chunks, start=1):
            chunks.append(
                KnowledgeChunk(
                    file=page.file,
                    page=page.page,
                    chunk_id=f"{stem}-p{page.page}-c{index}",
                    content=content,
                )
            )
    return chunks
