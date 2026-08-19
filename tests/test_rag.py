import json
from pathlib import Path

import numpy as np
import pytest

from app.core.config import Settings
from app.rag.indexer import build_index
from app.rag.loader import load_pdf_pages
from app.rag.retriever import KnowledgeRetriever
from app.rag.splitter import split_pages, split_text
from app.rag.vector_store import InvalidVectorStoreError, VectorStore
from app.tools.knowledge import search_company_docs


class KeywordEmbedder:
    model_name = "test/keyword-embedder"

    @staticmethod
    def _vector(text: str) -> np.ndarray:
        if "年假" in text or "考勤" in text:
            return np.asarray([0, 0, 0, 0, 1], dtype=np.float32)
        values = np.asarray(
            [
                sum(word in text for word in ("退款", "退货", "审核")),
                sum(word in text for word in ("物流", "发货", "顺丰")),
                sum(word in text for word in ("公司", "成立", "上海")),
                sum(word in text for word in ("产品", "A100", "设备")),
                sum(word in text for word in ("年假", "考勤")),
            ],
            dtype=np.float32,
        )
        norm = np.linalg.norm(values)
        return values / norm if norm else values

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        return np.vstack([self._vector(text) for text in texts]).astype(np.float32)

    def encode_query(self, text: str) -> np.ndarray:
        return self._vector(text)


def make_settings(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "knowledge_dir": Path("knowledge"),
        "vector_db_path": tmp_path / "vector_store",
        "embedding_model": KeywordEmbedder.model_name,
        "embedding_cache_dir": tmp_path / "model_cache",
        "chunk_size": 500,
        "chunk_overlap": 80,
        "rag_top_k": 3,
        "rag_score_threshold": 0.5,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_mock_pdfs_are_text_extractable_with_page_metadata() -> None:
    pages = load_pdf_pages(Path("knowledge"))

    assert [(page.file, page.page) for page in pages] == [
        ("company_intro.pdf", 1),
        ("product_manual.pdf", 1),
        ("refund_policy.pdf", 1),
        ("shipping_policy.pdf", 1),
    ]
    extracted = {page.file: page.content for page in pages}
    assert "成立于 2021 年" in extracted["company_intro.pdf"]
    assert "3 至 5 个工作日" in extracted["refund_policy.pdf"]
    assert "顺丰、中通和京东物流" in extracted["shipping_policy.pdf"]
    assert "A100" in extracted["product_manual.pdf"]


def test_splitter_produces_bounded_nonempty_stable_chunks() -> None:
    text = "第一段。" * 90 + "\n\n" + "第二段。" * 90
    pieces = split_text(text, chunk_size=120, chunk_overlap=20)

    assert len(pieces) > 2
    assert all(piece and len(piece) <= 120 for piece in pieces)

    pages = load_pdf_pages(Path("knowledge"))
    first = split_pages(pages, chunk_size=120, chunk_overlap=20)
    second = split_pages(pages, chunk_size=120, chunk_overlap=20)
    assert first == second
    assert all(chunk.chunk_id and chunk.file and chunk.page >= 1 for chunk in first)


def test_index_can_be_built_reloaded_and_validated(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    manifest = build_index(settings, KeywordEmbedder())
    store = VectorStore.load(settings.vector_db_path)

    assert manifest["embedding_model"] == KeywordEmbedder.model_name
    assert manifest["vector_count"] == store.index.ntotal == len(store.metadata) == 4
    assert manifest["dimension"] == 5
    assert {item["file"] for item in manifest["documents"]} == {
        "company_intro.pdf",
        "product_manual.pdf",
        "refund_policy.pdf",
        "shipping_policy.pdf",
    }
    assert all(chunk.content and chunk.chunk_id for chunk in store.metadata)


@pytest.mark.parametrize(
    ("question", "expected_file"),
    [
        ("退款多久到账？", "refund_policy.pdf"),
        ("已发货还能退款吗？", "refund_policy.pdf"),
        ("默认有哪些物流公司？", "shipping_policy.pdf"),
        ("公司创立于什么时候？", "company_intro.pdf"),
    ],
)
def test_fixed_questions_return_expected_sources(
    tmp_path: Path, question: str, expected_file: str
) -> None:
    settings = make_settings(tmp_path)
    embedder = KeywordEmbedder()
    build_index(settings, embedder)
    sources = KnowledgeRetriever(settings, embedder).retrieve(question)

    assert sources
    assert sources[0].file == expected_file
    assert sources[0].page == 1
    assert sources[0].chunk_id
    assert sources[0].content


def test_unrelated_question_returns_no_relevant_document(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    embedder = KeywordEmbedder()
    build_index(settings, embedder)
    retriever = KnowledgeRetriever(settings, embedder)

    result = search_company_docs("公司的年假有几天？", retriever)

    assert result.success is False
    assert result.error_code == "NO_RELEVANT_DOCUMENT"
    assert result.sources == []


def test_missing_index_returns_rag_not_ready(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    result = search_company_docs(
        "退款政策是什么？", KnowledgeRetriever(settings, KeywordEmbedder())
    )

    assert result.success is False
    assert result.error_code == "RAG_NOT_READY"
    assert "构建脚本" in result.message


def test_vector_count_mismatch_is_rejected(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    build_index(settings, KeywordEmbedder())
    metadata_path = settings.vector_db_path / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata_path.write_text(
        json.dumps(metadata[:-1], ensure_ascii=False), encoding="utf-8"
    )

    with pytest.raises(InvalidVectorStoreError, match="metadata"):
        VectorStore.load(settings.vector_db_path)
