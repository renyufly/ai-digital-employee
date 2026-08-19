import asyncio

import pytest

from app.agent.tool_registry import TOOL_REGISTRY, dispatch_tool, tool_schemas
from app.tools.calculator import calculate


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1280 * 0.8", 1024),
        ("(2 + 3) * 4 - 6 / 2", 17),
        ("17 % 5", 2),
        ("2 ** 10", 1024),
        ("-3 + +5", 2),
    ],
)
def test_calculator_supports_allowlisted_arithmetic(
    expression: str, expected: int | float
) -> None:
    result = calculate(expression)

    assert result.success is True
    assert result.data == {"expression": expression, "result": expected}
    assert result.error_code is None
    assert result.sources == []


@pytest.mark.parametrize(
    "expression",
    [
        "__import__('os').system('whoami')",
        "abs(-1)",
        "(1).__class__",
        "[1, 2]",
        "{'value': 1}",
        "'hello'",
        "True + 1",
    ],
)
def test_calculator_rejects_non_arithmetic_syntax(expression: str) -> None:
    result = calculate(expression)

    assert result.success is False
    assert result.data is None
    assert result.error_code == "CALCULATION_ERROR"


@pytest.mark.parametrize(
    "expression",
    [
        "1 / 0",
        "1 % 0",
        "2 ** 11",
        "1000000000001 + 1",
        "9" * 199,
        "999999999999 * 999999999999",
        "1 +",
        "",
        "1" * 201,
    ],
)
def test_calculator_maps_invalid_or_expensive_expressions(expression: str) -> None:
    result = calculate(expression)

    assert result.success is False
    assert result.error_code == "CALCULATION_ERROR"


def test_registry_dispatches_calculator_after_validation() -> None:
    result = asyncio.run(dispatch_tool("calculate", {"expression": "(8 + 2) / 5"}))

    assert result.success is True
    assert result.data is not None
    assert result.data["result"] == 2


@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"expression": 123},
        {"expression": "1 + 1", "unexpected": True},
        "not-an-object",
    ],
)
def test_registry_rejects_invalid_arguments(arguments: object) -> None:
    result = asyncio.run(dispatch_tool("calculate", arguments))

    assert result.success is False
    assert result.error_code == "INVALID_ARGUMENT"
    assert "参数无效" in result.message


def test_registry_rejects_unknown_tool() -> None:
    result = asyncio.run(dispatch_tool("run_anything", {"command": "whoami"}))

    assert result.success is False
    assert result.error_code == "UNKNOWN_TOOL"
    assert "未知工具" in result.message


def test_registry_rejects_non_string_tool_name() -> None:
    result = asyncio.run(
        dispatch_tool(["calculate"], {"expression": "1 + 1"})  # type: ignore[arg-type]
    )

    assert result.success is False
    assert result.error_code == "INVALID_ARGUMENT"
    assert result.message == "工具名必须是字符串"


def test_registry_exposes_only_explicit_tool_schemas() -> None:
    schemas = tool_schemas()

    assert set(TOOL_REGISTRY) == {
        "calculate",
        "query_order",
        "search_company_docs",
    }
    assert [schema["function"]["name"] for schema in schemas] == [
        "calculate",
        "query_order",
        "search_company_docs",
    ]
    for schema in schemas:
        parameters = schema["function"]["parameters"]
        assert parameters["additionalProperties"] is False
        assert parameters["required"]
