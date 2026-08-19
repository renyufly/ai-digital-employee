"""Build and persist the offline knowledge index."""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from app.core.config import Settings
from app.rag.embeddings import EmbeddingProvider, LocalBGEEmbedder
from app.rag.loader import load_pdf_pages
from app.rag.splitter import split_pages


def _write_json_atomic(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temporary, path)


def _document_manifest(knowledge_dir: Path) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    for path in sorted(knowledge_dir.glob("*.pdf"), key=lambda item: item.name.lower()):
        documents.append(
            {
                "file": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "size_bytes": path.stat().st_size,
            }
        )
    return documents


def build_index(
    settings: Settings, embedder: EmbeddingProvider | None = None
) -> dict[str, Any]:
    pages = load_pdf_pages(settings.knowledge_dir)
    chunks = split_pages(pages, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise ValueError("知识库没有产生任何 chunk")

    provider = embedder or LocalBGEEmbedder(
        settings.embedding_model, settings.embedding_cache_dir
    )
    vectors = np.asarray(
        provider.encode_documents([chunk.content for chunk in chunks]),
        dtype=np.float32,
    )
    if vectors.ndim != 2 or vectors.shape[0] != len(chunks):
        raise ValueError("Embedding 返回的向量数量与 chunk 数量不一致")

    output_dir = settings.vector_db_path
    output_dir.mkdir(parents=True, exist_ok=True)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    temporary_index = output_dir / "index.faiss.tmp"
    faiss.write_index(index, str(temporary_index))
    os.replace(temporary_index, output_dir / "index.faiss")

    metadata = [
        {
            "file": chunk.file,
            "page": chunk.page,
            "chunk_id": chunk.chunk_id,
            "content": chunk.content,
        }
        for chunk in chunks
    ]
    manifest = {
        "format_version": 1,
        "built_at": datetime.now(UTC).isoformat(),
        "embedding_model": provider.model_name,
        "dimension": int(vectors.shape[1]),
        "vector_count": len(chunks),
        "chunk_size": settings.chunk_size,
        "chunk_overlap": settings.chunk_overlap,
        "documents": _document_manifest(settings.knowledge_dir),
    }
    _write_json_atomic(output_dir / "metadata.json", metadata)
    _write_json_atomic(output_dir / "manifest.json", manifest)
    return manifest
