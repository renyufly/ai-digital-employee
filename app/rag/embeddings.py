"""Local normalized embeddings with a project-scoped model cache."""

from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

_BGE_QUERY_INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


class EmbeddingProvider(Protocol):
    model_name: str

    def encode_documents(self, texts: list[str]) -> NDArray[np.float32]: ...

    def encode_query(self, text: str) -> NDArray[np.float32]: ...


class LocalBGEEmbedder:
    """Load Sentence Transformers lazily so non-RAG commands stay lightweight."""

    def __init__(self, model_name: str, cache_dir: Path) -> None:
        self.model_name = model_name
        self._cache_dir = cache_dir
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._cache_dir.mkdir(parents=True, exist_ok=True)
            arguments = {
                "model_name_or_path": self.model_name,
                "cache_folder": str(self._cache_dir.resolve()),
            }
            try:
                self._model = SentenceTransformer(
                    **arguments,
                    local_files_only=True,
                )
            except OSError:
                self._model = SentenceTransformer(**arguments)
        return self._model

    def encode_documents(self, texts: list[str]) -> NDArray[np.float32]:
        vectors = self._get_model().encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=np.float32)

    def encode_query(self, text: str) -> NDArray[np.float32]:
        vector = self._get_model().encode(
            [_BGE_QUERY_INSTRUCTION + text],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vector[0], dtype=np.float32)
