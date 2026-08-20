import logging
from pathlib import Path

import pytest

from app.agent.schemas import ToolResult
from app.agent.service import AgentService
from app.core.config import Settings
from app.rag.indexer import build_index
from app.rag.retriever import KnowledgeRetriever
from app.agent.tool_registry import TOOL_REGISTRY, ToolDefinition, dispatch_tool
from tests.test_agent import FakeLLM, tool_call
from tests.test_rag import KeywordEmbedder
from app.llm.client import LLMResponse


@pytest.mark.asyncio
async def test_agent_logs_round_tool_status_and_duration_without_prompt(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret_prompt = "private-user-question-should-not-be-logged"
    fake = FakeLLM(
        [
            tool_call("call-1", "calculate", '{"expression":"2+2"}'),
            LLMResponse(content="结果是 4。"),
        ]
    )

    async def dispatcher(name: str, arguments: object) -> ToolResult:
        return ToolResult(success=True, data={"result": 4}, message="计算成功")

    settings = Settings(
        _env_file=None,
        openrouter_api_key="secret-key-that-must-not-appear",
        llm_model="openai/gpt-oss-20b:free",
    )
    with caplog.at_level(logging.INFO):
        await AgentService(fake, settings=settings, dispatcher=dispatcher).run(secret_prompt)

    log_text = caplog.text
    assert "Agent LLM round completed round=1" in log_text
    assert "tool=calculate success=True" in log_text
    assert "duration_ms=" in log_text
    assert secret_prompt not in log_text
    assert "secret-key-that-must-not-appear" not in log_text


def test_rag_logs_top_k_files_and_scores_but_not_query(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    settings = Settings(
        _env_file=None,
        knowledge_dir=Path("knowledge"),
        vector_db_path=tmp_path / "vector-store",
        embedding_model=KeywordEmbedder.model_name,
        embedding_cache_dir=tmp_path / "model-cache",
        rag_top_k=3,
        rag_score_threshold=0.5,
    )
    embedder = KeywordEmbedder()
    build_index(settings, embedder)
    private_query = "退款 private-query-marker"

    with caplog.at_level(logging.INFO):
        sources = KnowledgeRetriever(settings, embedder).retrieve(private_query)

    assert sources
    assert "top_k=3" in caplog.text
    assert "refund_policy.pdf" in caplog.text
    assert "scores=" in caplog.text
    assert private_query not in caplog.text


@pytest.mark.asyncio
async def test_tool_registry_logs_stack_for_unexpected_executor_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    original = TOOL_REGISTRY["calculate"]

    async def broken_executor(arguments: object) -> ToolResult:
        raise RuntimeError("diagnostic stack marker")

    monkeypatch.setitem(
        TOOL_REGISTRY,
        "calculate",
        ToolDefinition(
            name=original.name,
            description=original.description,
            input_model=original.input_model,
            executor=broken_executor,  # type: ignore[arg-type]
        ),
    )
    with caplog.at_level(logging.ERROR):
        result = await dispatch_tool("calculate", {"expression": "2+2"})

    assert result.error_code == "TOOL_INTERNAL_ERROR"
    assert "diagnostic stack marker" in caplog.text
    assert "Traceback" in caplog.text

