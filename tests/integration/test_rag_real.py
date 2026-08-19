from pathlib import Path

import pytest

from app.core.config import Settings
from app.rag.indexer import build_index
from app.rag.retriever import KnowledgeRetriever


@pytest.mark.integration
def test_real_bge_model_retrieves_expected_documents(tmp_path: Path) -> None:
    settings = Settings(
        _env_file=None,
        knowledge_dir=Path("knowledge"),
        vector_db_path=tmp_path / "vector_store",
        embedding_model="BAAI/bge-small-zh-v1.5",
        embedding_cache_dir=Path(".model-cache"),
        chunk_size=500,
        chunk_overlap=80,
        rag_top_k=3,
        rag_score_threshold=0.45,
    )
    build_index(settings)
    retriever = KnowledgeRetriever(settings)

    cases = [
        ("退款多久到账？", "refund_policy.pdf"),
        ("已发货还能退款吗？", "refund_policy.pdf"),
        ("默认有哪些物流公司？", "shipping_policy.pdf"),
        ("公司创立于什么时候？", "company_intro.pdf"),
    ]
    for question, expected_file in cases:
        sources = retriever.retrieve(question)
        assert expected_file in {source.file for source in sources[:3]}

    assert retriever.retrieve("公司的年假有几天？") == []
