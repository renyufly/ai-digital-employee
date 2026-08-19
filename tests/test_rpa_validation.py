import asyncio

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.rpa import order_query
from app.rpa.order_query import query_order


@pytest.mark.parametrize(
    ("order_no", "message"),
    [
        ("", "不能为空"),
        ("   ", "不能为空"),
        ("10001<script>", "只能包含"),
        ("1" * 33, "不能超过"),
    ],
)
def test_query_order_rejects_invalid_order_numbers(order_no: str, message: str) -> None:
    result = asyncio.run(query_order(order_no))

    assert result.success is False
    assert result.data is None
    assert result.error_code == "INVALID_ARGUMENT"
    assert message in result.message
    assert result.sources == []


def test_query_order_maps_playwright_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    async def time_out(_: str) -> dict[str, object]:
        raise PlaywrightTimeoutError("test timeout")

    monkeypatch.setattr(order_query, "_run_browser_query", time_out)

    result = asyncio.run(query_order("10001"))

    assert result.success is False
    assert result.error_code == "RPA_TIMEOUT"
    assert result.message == "ERP 页面操作超时"
