"""A deliberately small arithmetic evaluator built on an AST allowlist."""

from __future__ import annotations

import ast
import math
import operator
from collections.abc import Callable

from app.agent.schemas import ToolResult


_MAX_EXPRESSION_LENGTH = 200
_MAX_AST_NODES = 64
_MAX_NUMBER_ABS = 1_000_000_000_000
_MAX_RESULT_ABS = 1_000_000_000_000_000
_MAX_POWER_EXPONENT_ABS = 10

_BINARY_OPERATORS: dict[type[ast.operator], Callable[[int | float, int | float], int | float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}
_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[int | float], int | float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


class _CalculationFailure(Exception):
    """An expression that cannot be evaluated within the safe subset."""


def _validate_number(value: object, *, limit: int, label: str) -> int | float:
    if type(value) not in (int, float):
        raise _CalculationFailure("只允许使用普通整数或小数")
    # Check arbitrary-size integers before converting through math.isfinite,
    # which itself can overflow when handed a very large Python integer.
    if isinstance(value, int):
        if abs(value) > limit:
            raise _CalculationFailure(f"{label}绝对值不能超过 {limit}")
        return value
    if not math.isfinite(value):
        raise _CalculationFailure(f"{label}必须是有限数值")
    if abs(value) > limit:
        raise _CalculationFailure(f"{label}绝对值不能超过 {limit}")
    return value


def _evaluate_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Expression):
        return _evaluate_node(node.body)

    if isinstance(node, ast.Constant):
        return _validate_number(node.value, limit=_MAX_NUMBER_ABS, label="数字")

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        operand = _evaluate_node(node.operand)
        result = _UNARY_OPERATORS[type(node.op)](operand)
        return _validate_number(result, limit=_MAX_RESULT_ABS, label="计算结果")

    if isinstance(node, ast.BinOp):
        left = _evaluate_node(node.left)
        right = _evaluate_node(node.right)

        if isinstance(node.op, ast.Pow):
            if abs(right) > _MAX_POWER_EXPONENT_ABS:
                raise _CalculationFailure(
                    f"幂指数绝对值不能超过 {_MAX_POWER_EXPONENT_ABS}"
                )
            try:
                result = operator.pow(left, right)
            except (OverflowError, ValueError, ZeroDivisionError) as exc:
                raise _CalculationFailure("幂运算无法完成") from exc
        elif type(node.op) in _BINARY_OPERATORS:
            try:
                result = _BINARY_OPERATORS[type(node.op)](left, right)
            except ZeroDivisionError as exc:
                raise _CalculationFailure("不能除以零或对零取模") from exc
            except OverflowError as exc:
                raise _CalculationFailure("计算结果超出允许范围") from exc
        else:
            raise _CalculationFailure("只支持加、减、乘、除、取模和幂运算")

        return _validate_number(result, limit=_MAX_RESULT_ABS, label="计算结果")

    raise _CalculationFailure("表达式包含不允许的语法")


def _safe_evaluate(expression: str) -> int | float:
    if not isinstance(expression, str):
        raise _CalculationFailure("表达式必须是字符串")
    normalized = expression.strip()
    if not normalized:
        raise _CalculationFailure("表达式不能为空")
    if len(normalized) > _MAX_EXPRESSION_LENGTH:
        raise _CalculationFailure(
            f"表达式长度不能超过 {_MAX_EXPRESSION_LENGTH} 个字符"
        )

    try:
        parsed = ast.parse(normalized, mode="eval")
    except (SyntaxError, ValueError) as exc:
        raise _CalculationFailure("表达式语法错误") from exc

    if sum(1 for _ in ast.walk(parsed)) > _MAX_AST_NODES:
        raise _CalculationFailure("表达式过于复杂")

    result = _evaluate_node(parsed)
    if isinstance(result, float) and result.is_integer():
        return int(result)
    return result


def calculate(expression: str) -> ToolResult:
    """Calculate arithmetic from the safe subset and return a uniform result."""
    normalized = expression.strip() if isinstance(expression, str) else ""
    try:
        result = _safe_evaluate(expression)
        return ToolResult(
            success=True,
            data={"expression": normalized, "result": result},
            message="计算成功",
        )
    except _CalculationFailure as exc:
        return ToolResult(
            success=False,
            error_code="CALCULATION_ERROR",
            message=str(exc),
        )
    except Exception:
        return ToolResult(
            success=False,
            error_code="TOOL_INTERNAL_ERROR",
            message="计算工具发生内部错误",
        )
