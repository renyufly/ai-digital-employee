"""Explicit registry and safe dispatcher for tools available to the agent."""
''' Agent 的 工具注册中心Tool registry + 安全调度器dispatcher '''
'''
告诉LLM:有哪些工具可以调用、每个工具需要什么参数; 
LLM 真提出 Tool Call 后:再次校验工具名和参数; 
校验通过后:调用真正的 Python函数,并统一返回 ToolResult
'''
'''
LLM 只决策，不直接执行. 工具必须白名单化.
模型输出必须二次校验. 所有工具统一抽象.
'''

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
import logging
from typing import Any
import asyncio

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.agent.schemas import ToolResult
from app.rpa.order_query import query_order
from app.tools.calculator import calculate
from app.tools.knowledge import search_company_docs


logger = logging.getLogger(__name__)


class CalculateInput(BaseModel):
    '''
    通过继承pydantic的BaseModel，来验证calculate 工具允许接受什么参数.
    LLM 输出本质上是不可信输入，所以只允许定义过的字段
    '''
    model_config = ConfigDict(extra="forbid", strict=True) # 禁止额外字段, 严格类型校验

    '''
    同一个定义，同时description拿来生成给 LLM 看的 Schema，
    以及运行时给 Python 做真实参数校验.
    '''
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
# 类型别名->化简类型标注： def executor(model: BaseModel) -> Awaitable[ToolResult]:
# 一个异步函数，传进去一个 BaseModel，await 之后拿到 ToolResult


@dataclass(frozen=True)  # 该对象创建后不能随便修改. 是程序启动时定义好的安全白名单
class ToolDefinition:
    ''' 定义一个工具完整需要哪些元信息 '''
    """Everything needed to describe, validate, and execute one tool."""

    name: str
    description: str
    input_model: type[BaseModel]
    executor: ToolExecutor  # 真正执行它的 Python 函数


'''
适配器-Adapter Pattern: 让 Registry 只需要面对一种统一接口
'''
async def _execute_calculator(arguments: BaseModel) -> ToolResult:
    assert isinstance(arguments, CalculateInput) # 一个内部 invariant，让类型检查逻辑确认：运行到这里，类型必须符合预期
    return calculate(arguments.expression) # Calculator 本身是同步函数, 但包装成async，让dispatcher统一


async def _execute_order_query(arguments: BaseModel) -> ToolResult:
    assert isinstance(arguments, QueryOrderInput)
    return await query_order(arguments.order_no) # query_order()本身就是async


async def _execute_knowledge_search(arguments: BaseModel) -> ToolResult:
    assert isinstance(arguments, SearchCompanyDocsInput)
    ''' 
    search_company_docs()是同步函数, 且里面操作可能耗时, 会阻塞 asyncio Event Loop.
    asyncio.to_thread 会把 同步 RAG 丢给线程池，待完成后用await把结果返回
    '''
    return await asyncio.to_thread(search_company_docs, arguments.query)


TOOL_REGISTRY: Mapping[str, ToolDefinition] = {
    '''
    工具注册白名单.
    Mapping是说下面的程序只需要把它当成“可以读取的映射”，不要求修改能力.
    但只是类型接口层面表达只读意图，底层对象实际上仍是普通 dict，并没有真正做到运行时不可变
    '''

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
    ''' 统一 Tool 执行入口 '''
    """Validate model-proposed arguments again, then run an allowlisted tool."""

    if not isinstance(name, str):
        ''' 检查工具名类型. 因为LLM 给的任何东西都不能默认可信 '''
        return ToolResult(
            success=False,
            error_code="INVALID_ARGUMENT",
            message="工具名必须是字符串",
        )

    definition = TOOL_REGISTRY.get(name)
    if definition is None:
        ''' 检查 Tool 是否在TOOL_REGISTRY白名单里. '''
        return ToolResult(
            success=False,
            error_code="UNKNOWN_TOOL",
            message=f"未知工具：{name}",
        )

    try:
        '''
        参数二次校验. 因为Tool Schema 只是约束模型行为.
        Pydantic model_validate 才是真正执行前的程序校验
        '''
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
        '''
        真正执行工具-Tool calling executor
        '''
        return await definition.executor(validated)
    except Exception:
        logger.exception("Tool executor raised an unexpected error tool=%s", name)

        '''
        错误边界设计：不直接把 Python traceback 暴露给 LLM / API / 用户
        '''
        return ToolResult(
            success=False,
            error_code="TOOL_INTERNAL_ERROR",
            message=f"工具 {name} 执行失败",
        )


def tool_schemas() -> list[dict[str, Any]]:
    '''
    每个 ToolDefinition 转成 OpenAI/OpenRouter Tool Calling 所需的格式.
    tool_schemas() 不会执行任何工具, 它只是描述工具.
    真正执行工具的是：dispatch_tool()
    '''
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
