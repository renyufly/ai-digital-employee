"""Persistent FAISS index plus order-aligned JSON metadata."""
'''
把磁盘上的 FAISS 向量索引和对应的文档 Chunk 元数据加载进来，
并提供向量相似度搜索
'''
import json
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from numpy.typing import NDArray

from app.rag.models import KnowledgeChunk


class RAGNotReadyError(RuntimeError):
    ''' 表示 RAG 还没准备好，比如 index.faiss 根本没生成 '''
    """Raised when no complete local index is available."""


class InvalidVectorStoreError(RuntimeError):
    ''' 表示 索引存在，但数据对不上或损坏了，例如 4 个向量却只有 3 条 metadata '''
    """Raised when persisted vectors and metadata disagree."""


class VectorStore:
    def __init__(
        self,
        index: faiss.Index,
        metadata: list[KnowledgeChunk],
        manifest: dict[str, Any],
    ) -> None:
        self.index = index  # FAISS 向量索引，真正负责相似度搜索
        self.metadata = metadata
        self.manifest = manifest  # 索引的说明书，例如 embedding 模型、向量维度、向量数量等

    @classmethod
    def load(cls, directory: Path) -> "VectorStore":
        ''' 从磁盘恢复向量库 '''

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

        '''
        把 JSON 转成 KnowledgeChunk
        '''
        metadata = [KnowledgeChunk(**item) for item in raw_metadata]

        '''
        做三个 一致性检查
        '''
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
        '''
        真正执行向量搜索.
        注意：只负责 Top-K 搜索，并没有做阈值过滤。 
              项目中的相似度阈值过滤是在上层 Retriever 中完成
        '''

        '''
        保证用户问题变成 FAISS 要求的二维形式. (512,) -> (1, 512)
        1 表示：一次搜索 1 个问题向量
        '''
        vector = np.asarray(query_vector, dtype=np.float32).reshape(1, -1)

        if vector.shape[1] != self.index.d:
            raise InvalidVectorStoreError(
                f"查询向量维度 {vector.shape[1]} 与索引维度 {self.index.d} 不一致"
            )

        '''
        防止要求 Top-10，但知识库实际上只有 4 个 Chunk
        '''
        limit = min(top_k, len(self.metadata))

        ''' FAISS 返回
        scores  = 相似度分数
        indices = 对应向量在索引中的位置
        '''
        scores, indices = self.index.search(vector, limit)

        '''
        把 FAISS 的向量编号重新映射成真正的 KnowledgeChunk
        '''
        return [
            (self.metadata[index], float(score))
            for score, index in zip(scores[0], indices[0], strict=True)
            if index >= 0
        ]
