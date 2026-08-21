"""Local normalized embeddings with a project-scoped model cache."""
'''
封装本地 BGE Embedding 模型，把文档和用户问题转换成归一化向量，
供后续 FAISS 做语义检索
'''
'''
装了一个本地 BGE Embedding Provider，采用懒加载和项目级模型缓存。
文档和 Query 分别编码为 float32 归一化向量，
Query 额外添加 BGE 检索指令，之后交给 FAISS 做余弦语义检索.
'''

from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

# BGE 的检索指令前缀，帮助模型理解：这个文本是“查询”，我要拿它去搜索相关文档
_BGE_QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


class EmbeddingProvider(Protocol):
    '''
    接口约定，规定 Embedding 实现必须提供.
    以后想把 BGE 换成 OpenAI Embedding、BGE-M3 等，RAG 其他代码基本不用改
    '''
    model_name: str

    def encode_documents(self, texts: list[str]) -> NDArray[np.float32]: ...  # 文档 → 向量

    def encode_query(self, text: str) -> NDArray[np.float32]: ...  # # 用户问题 → 向量


class LocalBGEEmbedder:
    ''' 使用本地 SentenceTransformer 加载 BGE '''
    """Load Sentence Transformers lazily so non-RAG commands stay lightweight."""

    def __init__(self, model_name: str, cache_dir: Path) -> None:
        self.model_name = model_name
        self._cache_dir = cache_dir
        self._model = None # 初始化时不会马上加载模型，避免启动程序时就加载 PyTorch 和模型

    def _get_model(self):
        '''
        懒加载 + 本地缓存. 第一次真正需要 Embedding 时才执行.
        '''
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._cache_dir.mkdir(parents=True, exist_ok=True) # 创建缓存目录
            arguments = {
                "model_name_or_path": self.model_name,
                "cache_folder": str(self._cache_dir.resolve()),
            }
            try:
                self._model = SentenceTransformer(
                    **arguments,
                    local_files_only=True,
                )
                # 先尝试只从本地缓存加载模型. 然后再允许联网下载
            except OSError:
                self._model = SentenceTransformer(**arguments)

        return self._model

    def encode_documents(self, texts: list[str]) -> NDArray[np.float32]:
        ''' 文档转向量 '''
        '''
        encode() 传进去的是一个列表，它就会给列表里的每一条文本生成一个向量 (512维度)
        '''
        vectors = self._get_model().encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True, # 向量归一化。这样后面 FAISS 使用内积时，就可以等价地进行余弦相似度比较
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32) # FAISS 通常使用 float32

    def encode_query(self, text: str) -> NDArray[np.float32]:
        ''' 问题转向量 '''
        vector = self._get_model().encode(
            [_BGE_QUERY_INSTRUCTION + text],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        # 只输入了一个问题 [text]，所以只取第一条向量
        return np.asarray(vector[0], dtype=np.float32)
