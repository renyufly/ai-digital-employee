"""Load the offline index and return traceable retrieval sources."""

from app.agent.schemas import Source
from app.core.config import Settings, get_settings
from app.rag.embeddings import EmbeddingProvider, LocalBGEEmbedder
from app.rag.vector_store import InvalidVectorStoreError, VectorStore


class KnowledgeRetriever:
    def __init__(
        self,
        settings: Settings | None = None,
        embedder: EmbeddingProvider | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.embedder = embedder or LocalBGEEmbedder(
            self.settings.embedding_model, self.settings.embedding_cache_dir
        )
        self._store: VectorStore | None = None

    def _load_store(self) -> VectorStore:
        if self._store is None:
            self._store = VectorStore.load(self.settings.vector_db_path)
            indexed_model = self._store.manifest.get("embedding_model")
            if indexed_model != self.embedder.model_name:
                raise InvalidVectorStoreError(
                    f"索引模型 {indexed_model!r} 与当前模型 {self.embedder.model_name!r} 不一致"
                )
        return self._store

    def retrieve(self, query: str) -> list[Source]:
        normalized = query.strip()
        if not normalized:
            raise ValueError("知识库查询不能为空")
        if len(normalized) > 1000:
            raise ValueError("知识库查询不能超过 1000 个字符")

        store = self._load_store()
        matches = store.search(
            self.embedder.encode_query(normalized), self.settings.rag_top_k
        )
        if not matches:
            return []
        threshold = self.settings.rag_score_threshold
        if threshold is not None and matches[0][1] < threshold:
            return []
        return [
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
