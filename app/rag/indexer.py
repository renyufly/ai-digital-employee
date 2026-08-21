"""Build and persist the offline knowledge index."""
'''
离线索引构建部分：把 knowledge/ 目录里的 PDF 转成向量，
并保存成一个可供 RAG 检索的 FAISS 知识库.
'''
'''
把 PDF → Chunk → Embedding → FAISS，
同时保存来源 metadata 和索引配置 manifest，
为之后的 RAG 相似度检索做好准备
'''

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

'''
FAISS 是专门做向量相似度搜索的库，全名是 Facebook AI Similarity Search.
FAISS = 给我一个向量，帮我从大量向量中快速找到最相似的几个.
负责在已有向量中寻找距离它最近的.
注意：FAISS 不完全等于向量数据库，FAISS 更准确地说是一个向量搜索 / 向量索引库.
'''
import faiss
import numpy as np

from app.core.config import Settings
from app.rag.embeddings import EmbeddingProvider, LocalBGEEmbedder
from app.rag.loader import load_pdf_pages
from app.rag.splitter import split_pages


def _write_json_atomic(path: Path, value: Any) -> None:
    '''
    安全写 JSON. 不是直接覆盖正式文件, 避免程序写到一半崩溃，把原文件破坏掉
    '''
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temporary, path)


def _document_manifest(knowledge_dir: Path) -> list[dict[str, Any]]:
    '''
    给每个 PDF 记录: 文件名、sha哈希值(判断文档内容有没有发生变化)、文件大小
    '''
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
    '''建立索引index的核心函数'''

    ''' 读取 PDF 并切块'''
    pages = load_pdf_pages(settings.knowledge_dir)
    chunks = split_pages(pages, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise ValueError("知识库没有产生任何 chunk")

    ''' 
    调用embedder模型给所有 chunk 生成 Embedding.
    chunk1 文本 → 512维向量
    '''
    provider = embedder or LocalBGEEmbedder(
        settings.embedding_model, settings.embedding_cache_dir
    )
    '''
    返回的vectors的 shape = (chunk数量, 每个chunk的向量维度)
    '''
    vectors = np.asarray(
        provider.encode_documents([chunk.content for chunk in chunks]),
        dtype=np.float32,
    )
    if vectors.ndim != 2 or vectors.shape[0] != len(chunks):
        raise ValueError("Embedding 返回的向量数量与 chunk 数量不一致")

    output_dir = settings.vector_db_path
    output_dir.mkdir(parents=True, exist_ok=True)

    '''
    建立 FAISS 索引. IndexFlatIP 使用向量内积计算相似度.
    这里的内积 ≈ cosine similarity
    '''
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    # 保存到本地
    temporary_index = output_dir / "index.faiss.tmp"
    faiss.write_index(index, str(temporary_index)) 
    os.replace(temporary_index, output_dir / "index.faiss") # 向量

    '''
    FAISS 本身主要保存向量，所以还需要单独保存向量对应的原始信息.
    这样检索出向量后，才能知道它来自哪个 PDF、哪一页以及原文是什么
    '''
    metadata = [
        {
            "file": chunk.file,
            "page": chunk.page,
            "chunk_id": chunk.chunk_id,
            "content": chunk.content,
        }
        for chunk in chunks
    ]

    '''
    这个索引的说明书.
    '''
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
    _write_json_atomic(output_dir / "metadata.json", metadata) # 向量对应的原文/来源
    _write_json_atomic(output_dir / "manifest.json", manifest) # # 整个索引的配置和版本信息
    return manifest
