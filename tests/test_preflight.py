from collections import deque
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.agent.schemas import AgentResult, AgentTrace, Source
from app.core.config import Settings
from app.core.preflight import (
    DEMO_QUESTIONS,
    check_configuration,
    check_demo_questions,
    check_erp_seed,
    check_openrouter,
    check_vector_index,
)
from app.rag.indexer import build_index
from mock_erp.seed import seed_database
from tests.test_rag import KeywordEmbedder


def make_settings(tmp_path: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "openrouter_api_key": "super-secret-test-key",
        "llm_model": "openai/gpt-oss-20b:free",
        "mock_erp_database_path": tmp_path / "orders.db",
        "vector_db_path": tmp_path / "vector_store",
        "knowledge_dir": Path("knowledge"),
        "embedding_model": KeywordEmbedder.model_name,
        "embedding_cache_dir": tmp_path / "model-cache",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_preflight_validates_config_seed_and_vector_index_without_leaking_key(
    tmp_path: Path,
) -> None:
    settings = make_settings(tmp_path)
    seed_database(settings.mock_erp_database_path)
    build_index(settings, KeywordEmbedder())

    results = [
        check_configuration(settings),
        check_erp_seed(settings),
        check_vector_index(settings),
    ]

    assert all(result.status == "PASS" for result in results)
    assert "super-secret-test-key" not in " ".join(result.detail for result in results)


def test_preflight_reports_actionable_local_failures(tmp_path: Path) -> None:
    settings = make_settings(
        tmp_path,
        openrouter_api_key="",
        llm_model="openrouter/auto",
    )

    config = check_configuration(settings)
    seed = check_erp_seed(settings)
    index = check_vector_index(settings)

    assert config.status == seed.status == index.status == "FAIL"
    assert "OPENROUTER_API_KEY" in config.detail
    assert "数据库不存在" in seed.detail
    assert "索引尚未构建" in index.detail


@pytest.mark.asyncio
async def test_openrouter_check_verifies_tools_and_credit_balance(tmp_path: Path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/models"):
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "openai/gpt-oss-20b:free",
                            "supported_parameters": ["tools", "temperature"],
                        }
                    ]
                },
            )
        return httpx.Response(
            200, json={"data": {"total_credits": 10, "total_usage": 2.5}}
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://openrouter.test/api/v1"
    ) as client:
        results = await check_openrouter(make_settings(tmp_path), client)

    assert [result.status for result in results] == ["PASS", "PASS"]
    assert "tools" in results[0].detail
    assert "7.5000" in results[1].detail


class FakeAgent:
    def __init__(self, results: list[AgentResult]) -> None:
        self.results = deque(results)
        self.questions: list[str] = []

    async def run(self, user_message: str) -> AgentResult:
        self.questions.append(user_message)
        return self.results.popleft()


@pytest.mark.asyncio
async def test_demo_check_runs_each_core_question_once_and_enforces_tools_and_sources() -> None:
    source = Source(
        file="refund_policy.pdf",
        page=1,
        chunk_id="refund-p1-c1",
        content="退款政策",
        score=0.9,
    )

    def trace(name: str) -> AgentTrace:
        return AgentTrace(step=1, type="tool_result", name=name, summary="执行成功")

    fake = FakeAgent(
        [
            AgentResult(answer="退款回答", traces=[trace("search_company_docs")], sources=[source]),
            AgentResult(answer="订单回答", traces=[trace("query_order")]),
            AgentResult(
                answer="综合回答",
                traces=[trace("query_order"), trace("search_company_docs")],
                sources=[source],
            ),
        ]
    )

    results = await check_demo_questions(fake)

    assert fake.questions == [question for question, _, _ in DEMO_QUESTIONS]
    assert all(result.status == "PASS" for result in results)


@pytest.mark.asyncio
async def test_demo_check_fails_when_required_tool_or_source_is_missing() -> None:
    fake = FakeAgent([AgentResult(answer="没有工具或来源") for _ in DEMO_QUESTIONS])

    results = await check_demo_questions(fake)

    assert all(result.status == "FAIL" for result in results)


@pytest.mark.asyncio
async def test_demo_check_rejects_degenerate_repeated_character_answer() -> None:
    source = Source(
        file="refund_policy.pdf",
        page=1,
        chunk_id="refund-p1-c1",
        content="退款政策",
        score=0.9,
    )

    def traces(*names: str) -> list[AgentTrace]:
        return [
            AgentTrace(step=1, type="tool_result", name=name, summary="执行成功")
            for name in names
        ]

    fake = FakeAgent(
        [
            AgentResult(
                answer="!" * 100,
                traces=traces("search_company_docs"),
                sources=[source],
            ),
            AgentResult(answer="正常订单回答", traces=traces("query_order")),
            AgentResult(
                answer="正常综合回答",
                traces=traces("query_order", "search_company_docs"),
                sources=[source],
            ),
        ]
    )

    results = await check_demo_questions(fake)

    assert results[0].status == "FAIL"
    assert "重复字符" in results[0].detail
