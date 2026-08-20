"""Reusable, non-destructive checks for the interview demo environment."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import os
from pathlib import Path
import re
import socket
import sqlite3
from typing import Any, Literal, Protocol

import httpx
from playwright.async_api import Error as PlaywrightError, async_playwright

from app.agent.schemas import AgentResult
from app.core.config import Settings
from app.rag.vector_store import VectorStore


CheckStatus = Literal["PASS", "FAIL", "SKIP"]
_MODEL_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._:-]*$")


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    detail: str

    @property
    def passed(self) -> bool:
        return self.status != "FAIL"


class AgentRunner(Protocol):
    async def run(self, user_message: str) -> AgentResult: ...


def check_configuration(settings: Settings) -> CheckResult:
    """Validate secrets and model selection without printing secret values."""
    problems: list[str] = []
    if settings.llm_provider.lower() != "openrouter":
        problems.append("LLM_PROVIDER 必须为 openrouter")
    if not settings.openrouter_api_key or not settings.openrouter_api_key.strip():
        problems.append("OPENROUTER_API_KEY 未配置")
    model = settings.llm_model.strip()
    if (
        not _MODEL_ID_PATTERN.fullmatch(model)
        or model in {"openrouter/auto", "openrouter/free"}
    ):
        problems.append("LLM_MODEL 不是固定的 provider/model 完整 ID")
    if problems:
        return CheckResult(".env 配置", "FAIL", "；".join(problems))
    return CheckResult(".env 配置", "PASS", f"模型={model}，密钥已配置（值未输出）")


def check_erp_seed(settings: Settings) -> CheckResult:
    """Confirm the deterministic shipped and unshipped demo rows exist."""
    database_path = settings.mock_erp_database_path
    if not database_path.is_file():
        return CheckResult("ERP seed 数据", "FAIL", f"数据库不存在：{database_path}")
    try:
        with sqlite3.connect(database_path) as connection:
            rows = connection.execute(
                "SELECT order_no, status FROM orders WHERE order_no IN (?, ?)",
                ("10001", "10002"),
            ).fetchall()
    except sqlite3.Error as exc:
        return CheckResult("ERP seed 数据", "FAIL", f"数据库无法读取：{exc}")
    statuses = {str(order_no): str(status) for order_no, status in rows}
    if statuses.get("10001") != "已发货" or statuses.get("10002") != "处理中":
        return CheckResult(
            "ERP seed 数据",
            "FAIL",
            "需要重新运行 scripts/seed_erp.py（期望 10001=已发货、10002=处理中）",
        )
    return CheckResult("ERP seed 数据", "PASS", "10001=已发货，10002=处理中")


def check_vector_index(settings: Settings) -> CheckResult:
    """Load and validate all persisted FAISS artifacts without embedding a query."""
    try:
        store = VectorStore.load(settings.vector_db_path)
    except Exception as exc:
        return CheckResult("RAG 向量索引", "FAIL", str(exc))
    indexed_model = store.manifest.get("embedding_model")
    if indexed_model != settings.embedding_model:
        return CheckResult(
            "RAG 向量索引",
            "FAIL",
            f"索引模型={indexed_model}，当前配置模型={settings.embedding_model}",
        )
    files = sorted({chunk.file for chunk in store.metadata})
    return CheckResult(
        "RAG 向量索引",
        "PASS",
        f"向量={store.index.ntotal}，文档={','.join(files)}",
    )


def check_ports_available(ports: Iterable[int] = (8000, 8001, 8501)) -> CheckResult:
    """Verify standard demo ports are bindable before services are started."""
    occupied: list[int] = []
    for port in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", port))
        except OSError:
            occupied.append(port)
    if occupied:
        return CheckResult("演示端口", "FAIL", f"端口被占用：{','.join(map(str, occupied))}")
    return CheckResult("演示端口", "PASS", "8000、8001、8501 均可用")


async def check_chromium(settings: Settings) -> CheckResult:
    """Actually launch the project-local Chromium once, then close it."""
    browser_root = settings.playwright_browsers_path.resolve()
    if not browser_root.is_dir():
        return CheckResult("项目内 Chromium", "FAIL", f"目录不存在：{browser_root}")
    previous = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browser_root)
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            await browser.close()
    except PlaywrightError as exc:
        return CheckResult("项目内 Chromium", "FAIL", f"启动失败：{exc}")
    finally:
        if previous is None:
            os.environ.pop("PLAYWRIGHT_BROWSERS_PATH", None)
        else:
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = previous
    return CheckResult("项目内 Chromium", "PASS", str(browser_root))


async def check_openrouter(
    settings: Settings,
    client: httpx.AsyncClient | None = None,
) -> list[CheckResult]:
    """Check network/auth, model tool support, and the account credit endpoint."""
    headers = {"Authorization": f"Bearer {settings.openrouter_api_key or ''}"}
    owns_client = client is None
    http = client or httpx.AsyncClient(
        base_url=settings.llm_base_url.rstrip("/"),
        headers=headers,
        timeout=10,
    )
    results: list[CheckResult] = []
    try:
        models_response = await http.get("/models")
        models_response.raise_for_status()
        payload = models_response.json()
        models = payload.get("data", []) if isinstance(payload, dict) else []
        selected = next(
            (item for item in models if item.get("id") == settings.llm_model), None
        )
        if selected is None:
            results.append(
                CheckResult("OpenRouter 网络与模型", "FAIL", "配置模型未出现在 Models API")
            )
        elif "tools" not in selected.get("supported_parameters", []):
            results.append(
                CheckResult("OpenRouter 网络与模型", "FAIL", "配置模型未声明支持 tools")
            )
        else:
            results.append(
                CheckResult("OpenRouter 网络与模型", "PASS", "网络、鉴权和 tools 能力正常")
            )

        credits_response = await http.get("/credits")
        credits_response.raise_for_status()
        credits_payload = credits_response.json()
        credit_data = credits_payload.get("data", credits_payload)
        total = float(credit_data["total_credits"])
        used = float(credit_data["total_usage"])
        remaining = total - used
        if remaining <= 0 and not settings.llm_model.endswith(":free"):
            results.append(CheckResult("OpenRouter 余额", "FAIL", "可用余额不足"))
        else:
            results.append(
                CheckResult("OpenRouter 余额", "PASS", f"剩余额度={remaining:.4f}")
            )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
        results.append(
            CheckResult("OpenRouter 联网检查", "FAIL", f"请求或响应异常：{type(exc).__name__}")
        )
    finally:
        if owns_client:
            await http.aclose()
    return results


async def check_erp_service(settings: Settings) -> CheckResult:
    """Confirm the Mock ERP is reachable before running real RPA demos."""
    try:
        async with httpx.AsyncClient(timeout=3, follow_redirects=True) as client:
            response = await client.get(f"{settings.mock_erp_url.rstrip('/')}/login")
            response.raise_for_status()
    except httpx.HTTPError as exc:
        return CheckResult("Mock ERP 服务", "FAIL", f"无法访问登录页：{type(exc).__name__}")
    return CheckResult("Mock ERP 服务", "PASS", settings.mock_erp_url)


DEMO_QUESTIONS: tuple[tuple[str, set[str], bool], ...] = (
    ("退款多久到账？", {"search_company_docs"}, True),
    ("帮我查询订单 10001。", {"query_order"}, False),
    (
        "查询订单 10001，如果已经发货，告诉我物流信息，同时根据公司的退款政策告诉我是否还能申请退款。",
        {"query_order", "search_company_docs"},
        True,
    ),
)


def _answer_is_degenerate(answer: str) -> bool:
    compact = "".join(answer.split())
    return not compact or (len(compact) >= 20 and len(set(compact)) < 4)


async def check_demo_questions(agent: AgentRunner) -> list[CheckResult]:
    """Run each fixed interview question once and verify its observable contract."""
    results: list[CheckResult] = []
    for index, (question, required_tools, require_sources) in enumerate(DEMO_QUESTIONS, 1):
        try:
            result = await agent.run(question)
        except Exception as exc:
            results.append(
                CheckResult(f"示例问题 {index}", "FAIL", f"执行异常：{type(exc).__name__}")
            )
            continue
        used_tools = {
            trace.name for trace in result.traces if trace.type == "tool_result" and trace.name
        }
        missing_tools = required_tools - used_tools
        if result.error_code:
            detail = f"error_code={result.error_code}"
            status: CheckStatus = "FAIL"
        elif _answer_is_degenerate(result.answer):
            detail = "模型回答为空或明显退化为重复字符"
            status = "FAIL"
        elif missing_tools:
            detail = f"缺少工具：{','.join(sorted(missing_tools))}"
            status = "FAIL"
        elif require_sources and not result.sources:
            detail = "回答没有 RAG 来源"
            status = "FAIL"
        else:
            detail = f"工具={','.join(sorted(used_tools)) or '-'}，来源={len(result.sources)}"
            status = "PASS"
        results.append(CheckResult(f"示例问题 {index}", status, detail))
    return results
