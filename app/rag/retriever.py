"""Load the offline index and return traceable retrieval sources."""
'''
在线检索阶段：
加载已经构建好的 FAISS 知识库索引，把用户问题转成向量进行检索，
并返回带来源信息的相关文档片段.
'''
'''
用户问题
 → 校验
 → BGE 转向量
 → 加载 FAISS
 → Top-K 相似度检索 (Top-K: 按相似度从高到低, 取相似度最高的 K 个Chunk)
 → 阈值过滤  (相似度至少达到 threshold阈值，才认为这个 Chunk 和问题足够相关. 
 可能删除top-k中的不符合chunk)
 → 包装成带来源的 Source
 → 返回给 Agent.
 只负责“找资料”，不负责让 LLM 生成最终答案，这也是 RAG 与 Agent 解耦.
'''

import logging

from app.agent.schemas import Source
from app.core.config import Settings, get_settings
from app.rag.embeddings import EmbeddingProvider, LocalBGEEmbedder
from app.rag.vector_store import InvalidVectorStoreError, VectorStore


logger = logging.getLogger(__name__)


class KnowledgeRetriever:
    def __init__(
        self,
        settings: Settings | None = None,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        '''
        准备配置、Embedding 和向量库
        '''
        self.settings = settings or get_settings()
        self.embedder = embedder or LocalBGEEmbedder(
            self.settings.embedding_model, self.settings.embedding_cache_dir
        ) # 用来把用户问题转换成向量
        self._store: VectorStore | None = None

    def _load_store(self) -> VectorStore:
        ''' 加载向量数据库 '''
        if self._store is None:
            self._store = VectorStore.load(self.settings.vector_db_path)
            indexed_model = self._store.manifest.get("embedding_model")
            if indexed_model != self.embedder.model_name:
                '''
                确保建立索引时使用的 Embedding 模型 = 当前查询使用的 Embedding 模型.
                否则两个模型产生的向量空间不同，相似度比较没有意义，所以直接报错
                '''
                raise InvalidVectorStoreError(
                    f"索引模型 {indexed_model!r} 与当前模型 {self.embedder.model_name!r} 不一致"
                )
        return self._store

    def retrieve(self, query: str) -> list[Source]:
        ''' 真正执行 RAG 检索 '''

        normalized = query.strip() 
        ''' 
        清理和检查问题:禁止空问题和超过 1000 字符的问题 
        '''
        if not normalized:
            raise ValueError("知识库查询不能为空")
        if len(normalized) > 1000:
            raise ValueError("知识库查询不能超过 1000 个字符")

        store = self._load_store() # 加载向量数据库
        '''
        用户问题 -> BGE encode_query() ->问题向量
        FAISS search() -> Top-K 最相似 Chunk
        '''
        matches = store.search(
            self.embedder.encode_query(normalized), self.settings.rag_top_k
        )
        if not matches:
            logger.info("RAG retrieval completed top_k=%d matches=0", self.settings.rag_top_k)
            return []

        threshold = self.settings.rag_score_threshold
        if threshold is not None and matches[0][1] < threshold:
            '''
            相似度阈值过滤: 如果最相关的一条都低于阈值，说明整个知识库大概率没有相关内容，直接返回空.
            减少“硬拿不相关文档回答”的情况。项目当前 RAG 使用 Top-K + 阈值过滤，并返回可追踪来源
            '''
            logger.info(
                "RAG retrieval completed top_k=%d matches=0 threshold=%s best_score=%.4f",
                self.settings.rag_top_k,
                threshold,
                matches[0][1],
            )
            return []

        '''
        把检索结果整理成统一格式. 方便Agent 不仅能拿到文档内容，
        还能展示文件名、页码、Chunk ID、相似度
        '''
        sources = [
            Source(
                file=chunk.file,
                page=chunk.page,
                chunk_id=chunk.chunk_id,
                content=chunk.content,
                score=score,
            )
            for chunk, score in matches
            if threshold is None or score >= threshold
        ]

        logger.info(
            "RAG retrieval completed top_k=%d matches=%d files=%s scores=%s",
            self.settings.rag_top_k,
            len(sources),
            ",".join(source.file for source in sources) or "-",
            ",".join(f"{source.score:.4f}" for source in sources) or "-",
        )

        return sources
