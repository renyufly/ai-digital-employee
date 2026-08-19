"""Internal immutable records used by the RAG pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PageDocument:
    file: str
    page: int
    content: str


@dataclass(frozen=True)
class KnowledgeChunk:
    file: str
    page: int
    chunk_id: str
    content: str
