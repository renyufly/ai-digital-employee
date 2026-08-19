"""Explicit registry and safe dispatcher for tools available to the agent."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any
import asyncio

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.agent.schemas import ToolResult
from app.rpa.order_query import query_order
from app.tools.calculator import calculate
from app.tools.knowledge import search_company_docs


class CalculateInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expression: str = Field(
        min_length=1,
        max_length=200,
        description="只包含数字、括号及基础算术运算符的表达式",
    )


class QueryOrderInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    order_no: str = Field(
        min_length=1,
        max_length=32,
        description="要在 Mock ERP 中查询的订单号",
    )


class SearchCompanyDocsInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    query: str = Field(
        min_length=1,
        max_length=1000,
        description="要在企业政策、物流说明、公司介绍或产品手册中检索的问题",
    )


ToolExecutor = Callable[[BaseModel], Awaitable[ToolResult]]


@dataclass(frozen=True)
class ToolDefinition:
    """Everything needed to describe, validate, and execute one tool."""

    name: str
    description: str
    input_model: type[BaseModel]
    executor: ToolExecutor


async def _execute_calculator(arguments: BaseModel) -> ToolResult:
    assert isinstance(arguments, CalculateInput)
    return calculate(arguments.expression)


async def _execute_order_query(arguments: BaseModel) -> ToolResult:
    assert isinstance(arguments, QueryOrderInput)
    return await query_order(arguments.order_no)


async def _execute_knowledge_search(arguments: BaseModel) -> ToolResult:
    assert isinstance(arguments, SearchCompanyDocsInput)
    return await asyncio.to_thread(search_company_docs, arguments.query)


TOOL_REGISTRY: Mapping[str, ToolDefinition] = {
    "calculate": ToolDefinition(
        name="calculate",
        description="进行安全的基础数学计算，支持括号、加减乘除、取模和有限幂运算。",
        input_model=CalculateInput,
        executor=_execute_calculator,
    ),
    "query_order": ToolDefinition(
        name="query_order",
        description="通过企业 ERP 查询指定订单的状态、金额和物流信息。",
        input_model=QueryOrderInput,
        executor=_execute_order_query,
    ),
    "search_company_docs": ToolDefinition(
        name="search_company_docs",
        description="搜索企业内部知识库，用于回答公司政策、产品说明、物流政策和退款政策等问题。",
        input_model=SearchCompanyDocsInput,
        executor=_execute_knowledge_search,
    ),
}


async def dispatch_tool(name: str, arguments: object) -> ToolResult:
    """Validate model-proposed arguments again, then run an allowlisted tool."""
    if not isinstance(name, str):
        return ToolResult(
            success=False,
            error_code="INVALID_ARGUMENT",
            message="工具名必须是字符串",
        )
    definition = TOOL_REGISTRY.get(name)
    if definition is None:
        return ToolResult(
            success=False,
            error_code="UNKNOWN_TOOL",
            message=f"未知工具：{name}",
        )

    try:
        validated = definition.input_model.model_validate(arguments)
    except ValidationError as exc:
        errors = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        return ToolResult(
            success=False,
            error_code="INVALID_ARGUMENT",
            message=f"工具 {name} 的参数无效：{errors}",
        )

    try:
        return await definition.executor(validated)
    except Exception:
        return ToolResult(
            success=False,
            error_code="TOOL_INTERNAL_ERROR",
            message=f"工具 {name} 执行失败",
        )


def tool_schemas() -> list[dict[str, Any]]:
    """Expose deterministic OpenAI-compatible schemas for a later LLM client."""
    return [
        {
            "type": "function",
            "function": {
                "name": definition.name,
                "description": definition.description,
                "parameters": definition.input_model.model_json_schema(),
            },
        }
        for definition in TOOL_REGISTRY.values()
    ]
