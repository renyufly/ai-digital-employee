"""Persistent FAISS index plus order-aligned JSON metadata."""

import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from numpy.typing import NDArray

from app.rag.models import KnowledgeChunk


class RAGNotReadyError(RuntimeError):
    """Raised when no complete local index is available."""


class InvalidVectorStoreError(RuntimeError):
    """Raised when persisted vectors and metadata disagree."""


class VectorStore:
    def __init__(
        self,
        index: faiss.Index,
        metadata: list[KnowledgeChunk],
        manifest: dict[str, Any],
    ) -> None:
        self.index = index
        self.metadata = metadata
        self.manifest = manifest

    @classmethod
    def load(cls, directory: Path) -> "VectorStore":
        index_path = directory / "index.faiss"
        metadata_path = directory / "metadata.json"
        manifest_path = directory / "manifest.json"
        missing = [
            path.name
            for path in (index_path, metadata_path, manifest_path)
            if not path.is_file()
        ]
        if missing:
            raise RAGNotReadyError(
                f"RAG 索引尚未构建，缺少 {', '.join(missing)}；请先运行构建脚本"
            )

        index = faiss.read_index(str(index_path))
        raw_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        metadata = [KnowledgeChunk(**item) for item in raw_metadata]

        if index.ntotal != len(metadata):
            raise InvalidVectorStoreError(
                f"向量数量 {index.ntotal} 与 metadata 数量 {len(metadata)} 不一致"
            )
        if manifest.get("vector_count") != len(metadata):
            raise InvalidVectorStoreError("manifest 中的向量数量与 metadata 不一致")
        if manifest.get("dimension") != index.d:
            raise InvalidVectorStoreError("manifest 中的向量维度与 FAISS 索引不一致")
        return cls(index=index, metadata=metadata, manifest=manifest)

    def search(
        self, query_vector: NDArray[np.float32], top_k: int
    ) -> list[tuple[KnowledgeChunk, float]]:
        vector = np.asarray(query_vector, dtype=np.float32).reshape(1, -1)
        if vector.shape[1] != self.index.d:
            raise InvalidVectorStoreError(
                f"查询向量维度 {vector.shape[1]} 与索引维度 {self.index.d} 不一致"
            )
        limit = min(top_k, len(self.metadata))
        scores, indices = self.index.search(vector, limit)
        return [
            (self.metadata[index], float(score))
            for score, index in zip(scores[0], indices[0], strict=True)
            if index >= 0
        ]
