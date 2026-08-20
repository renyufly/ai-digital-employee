"""Query the legacy-style Mock ERP exclusively through its web interface."""

from __future__ import annotations

import logging
import os
import re
from time import perf_counter
from urllib.parse import urljoin

from playwright.async_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from app.agent.schemas import ToolResult
from app.core.config import get_settings


logger = logging.getLogger(__name__)
_ORDER_NO_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_MAX_ORDER_NO_LENGTH = 32


class _RpaFailure(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


def _validate_order_no(order_no: str) -> str:
    if not isinstance(order_no, str):
        raise _RpaFailure("INVALID_ARGUMENT", "订单号必须是字符串")
    normalized = order_no.strip()
    if not normalized:
        raise _RpaFailure("INVALID_ARGUMENT", "订单号不能为空")
    if len(normalized) > _MAX_ORDER_NO_LENGTH:
        raise _RpaFailure("INVALID_ARGUMENT", "订单号长度不能超过 32 个字符")
    if _ORDER_NO_PATTERN.fullmatch(normalized) is None:
        raise _RpaFailure("INVALID_ARGUMENT", "订单号只能包含字母、数字、下划线和连字符")
    return normalized


async def _require_visible(page: Page, test_id: str, stage: str) -> None:
    try:
        await page.get_by_test_id(test_id).wait_for(state="visible")
    except PlaywrightTimeoutError as exc:
        raise _RpaFailure(
            "ERP_PAGE_CHANGED", f"ERP 页面结构发生变化：未找到{stage}元素"
        ) from exc


async def _require_attached(page: Page, test_id: str, stage: str) -> None:
    try:
        await page.get_by_test_id(test_id).wait_for(state="attached")
    except PlaywrightTimeoutError as exc:
        raise _RpaFailure(
            "ERP_PAGE_CHANGED", f"ERP 页面结构发生变化：未找到{stage}元素"
        ) from exc


async def _open_login(page: Page, login_url: str, timeout_ms: int) -> None:
    try:
        response = await page.goto(
            login_url, wait_until="domcontentloaded", timeout=timeout_ms
        )
    except PlaywrightTimeoutError as exc:
        raise _RpaFailure("RPA_TIMEOUT", "打开 ERP 登录页超时") from exc
    except PlaywrightError as exc:
        raise _RpaFailure("ERP_UNAVAILABLE", "无法连接 Mock ERP，请确认服务已启动") from exc
    if response is None or response.status >= 500:
        raise _RpaFailure("ERP_UNAVAILABLE", "Mock ERP 当前不可用")


async def _login(page: Page, username: str, password: str) -> None:
    await _require_visible(page, "username", "用户名输入框")
    await _require_visible(page, "password", "密码输入框")
    await _require_visible(page, "login-submit", "登录按钮")
    await page.get_by_test_id("username").fill(username)
    await page.get_by_test_id("password").fill(password)
    await page.get_by_test_id("login-submit").click()
    await page.wait_for_load_state("domcontentloaded")

    if await page.get_by_test_id("login-error").is_visible():
        raise _RpaFailure("ERP_LOGIN_FAILED", "ERP 登录失败，请检查用户名和密码")
    try:
        await page.get_by_test_id("order-search").wait_for(state="visible")
    except PlaywrightTimeoutError as exc:
        raise _RpaFailure("ERP_LOGIN_FAILED", "ERP 登录后未进入订单页面") from exc


async def _search_and_open_order(page: Page, order_no: str) -> None:
    await _require_visible(page, "order-search", "订单搜索框")
    await _require_visible(page, "order-search-submit", "订单查询按钮")
    await page.get_by_test_id("order-search").fill(order_no)
    await page.get_by_test_id("order-search-submit").click()
    await page.wait_for_load_state("domcontentloaded")

    if await page.get_by_test_id("order-message").is_visible():
        message = (await page.get_by_test_id("order-message").inner_text()).strip()
        if "未找到订单" in message:
            raise _RpaFailure("ORDER_NOT_FOUND", f"未找到订单 {order_no}")
        raise _RpaFailure("ERP_PAGE_CHANGED", f"ERP 查询失败：{message}")

    link = page.get_by_test_id(f"order-link-{order_no}")
    try:
        await link.wait_for(state="visible")
        await link.click()
        await page.wait_for_load_state("domcontentloaded")
    except PlaywrightTimeoutError as exc:
        raise _RpaFailure("ERP_PAGE_CHANGED", "ERP 查询结果页面结构发生变化") from exc


async def _read_order(page: Page) -> dict[str, str | float | None]:
    field_ids = {
        "order_no": "order-no",
        "customer_name": "customer-name",
        "amount": "amount",
        "status": "status",
        "shipping_company": "shipping-company",
        "tracking_number": "tracking-number",
        "created_at": "created-at",
        "shipped_at": "shipped-at",
    }
    values: dict[str, str] = {}
    for key, test_id in field_ids.items():
        # Optional logistics fields are intentionally empty for unshipped orders,
        # so their elements must exist but do not need to satisfy Playwright's
        # visual "visible" definition.
        await _require_attached(page, test_id, f"订单详情 {key}")
        values[key] = (await page.get_by_test_id(test_id).inner_text()).strip()

    try:
        amount = float(values["amount"].replace("¥", "").replace(",", ""))
    except ValueError as exc:
        raise _RpaFailure("ERP_PAGE_CHANGED", "ERP 订单金额格式无法识别") from exc

    return {
        "order_no": values["order_no"],
        "customer_name": values["customer_name"],
        "amount": amount,
        "status": values["status"],
        "shipping_company": values["shipping_company"] or None,
        "tracking_number": values["tracking_number"] or None,
        "created_at": values["created_at"],
        "shipped_at": values["shipped_at"] or None,
    }


async def _run_browser_query(order_no: str) -> dict[str, str | float | None]:
    settings = get_settings()
    browser_path = settings.playwright_browsers_path.resolve()
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(browser_path))
    login_url = urljoin(settings.mock_erp_url.rstrip("/") + "/", "login")
    browser: Browser | None = None
    context: BrowserContext | None = None

    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(headless=settings.rpa_headless)
            context = await browser.new_context()
            page = await context.new_page()
            page.set_default_timeout(settings.rpa_timeout_ms)
            await _open_login(page, login_url, settings.rpa_timeout_ms)
            logger.info("RPA ERP login page opened order_no=%s", order_no)
            await _login(page, settings.mock_erp_username, settings.mock_erp_password)
            logger.info("RPA ERP login succeeded order_no=%s", order_no)
            logger.info("RPA ERP order search started order_no=%s", order_no)
            await _search_and_open_order(page, order_no)
            logger.info("RPA ERP order detail opened order_no=%s", order_no)
            result = await _read_order(page)
            logger.info("RPA ERP order detail read order_no=%s", order_no)
            return result
        finally:
            if context is not None:
                try:
                    await context.close()
                except PlaywrightError:
                    logger.warning("Failed to close RPA browser context", exc_info=True)
            if browser is not None:
                try:
                    await browser.close()
                except PlaywrightError:
                    logger.warning("Failed to close RPA browser", exc_info=True)


async def query_order(order_no: str) -> ToolResult:
    """Log in and query one order through a fresh Playwright browser session."""
    started_at = perf_counter()
    normalized_order_no = "<invalid>"

    try:
        normalized_order_no = _validate_order_no(order_no)
        logger.info("RPA order query started order_no=%s", normalized_order_no)
        data = await _run_browser_query(normalized_order_no)

        duration_ms = int((perf_counter() - started_at) * 1000)
        logger.info(
            "RPA order query succeeded order_no=%s duration_ms=%d",
            normalized_order_no,
            duration_ms,
        )
        return ToolResult(success=True, data=data, message="订单查询成功")
    except _RpaFailure as exc:
        logger.warning(
            "RPA order query failed order_no=%s error_code=%s message=%s",
            normalized_order_no,
            exc.error_code,
            exc.message,
        )
        return ToolResult(success=False, error_code=exc.error_code, message=exc.message)
    except PlaywrightTimeoutError:
        logger.exception("RPA operation timed out order_no=%s", normalized_order_no)
        return ToolResult(success=False, error_code="RPA_TIMEOUT", message="ERP 页面操作超时")
    except PlaywrightError:
        logger.exception("Unexpected Playwright failure order_no=%s", normalized_order_no)
        return ToolResult(
            success=False,
            error_code="TOOL_INTERNAL_ERROR",
            message="浏览器自动化执行失败",
        )
    except Exception:
        logger.exception("Unexpected RPA failure order_no=%s", normalized_order_no)
        return ToolResult(
            success=False,
            error_code="TOOL_INTERNAL_ERROR",
            message="订单查询工具发生内部错误",
        )
