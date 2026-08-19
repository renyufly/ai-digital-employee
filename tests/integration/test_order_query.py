from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from app.core.config import get_settings
from app.rpa.order_query import query_order
from mock_erp.seed import seed_database


pytestmark = pytest.mark.integration


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def live_mock_erp(tmp_path_factory: pytest.TempPathFactory) -> Iterator[str]:
    port = _free_port()
    database_path = tmp_path_factory.mktemp("rpa-erp") / "orders.db"
    seed_database(database_path)
    env = os.environ.copy()
    env["MOCK_ERP_DATABASE_PATH"] = str(database_path)
    env["MOCK_ERP_USERNAME"] = "admin"
    env["MOCK_ERP_PASSWORD"] = "admin123"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "mock_erp.app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"{base_url}/login", timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.05)
        else:
            raise RuntimeError("Mock ERP did not start in time")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


@pytest.fixture(autouse=True)
def configure_rpa(monkeypatch: pytest.MonkeyPatch, live_mock_erp: str) -> Iterator[None]:
    monkeypatch.setenv("MOCK_ERP_URL", live_mock_erp)
    monkeypatch.setenv("MOCK_ERP_USERNAME", "admin")
    monkeypatch.setenv("MOCK_ERP_PASSWORD", "admin123")
    monkeypatch.setenv("RPA_HEADLESS", "true")
    monkeypatch.setenv("RPA_TIMEOUT_MS", "5000")
    monkeypatch.setenv(
        "PLAYWRIGHT_BROWSERS_PATH",
        str(Path(__file__).resolve().parents[2] / ".playwright-browsers"),
    )
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_query_shipped_order() -> None:
    result = asyncio.run(query_order("10001"))

    assert result.success is True
    assert result.error_code is None
    assert result.data == {
        "order_no": "10001",
        "customer_name": "张三",
        "amount": 1280.0,
        "status": "已发货",
        "shipping_company": "顺丰",
        "tracking_number": "SF123456789",
        "created_at": "2026-08-17 09:30",
        "shipped_at": "2026-08-18 13:20",
    }


def test_query_processing_and_missing_orders() -> None:
    processing = asyncio.run(query_order("10002"))
    missing = asyncio.run(query_order("99999"))

    assert processing.success is True
    assert processing.data is not None
    assert processing.data["status"] == "处理中"
    assert processing.data["shipping_company"] is None
    assert processing.data["tracking_number"] is None
    assert processing.data["shipped_at"] is None
    assert missing.success is False
    assert missing.error_code == "ORDER_NOT_FOUND"


def test_wrong_password_returns_login_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOCK_ERP_PASSWORD", "wrong-password")
    get_settings.cache_clear()

    result = asyncio.run(query_order("10001"))

    assert result.success is False
    assert result.error_code == "ERP_LOGIN_FAILED"

    monkeypatch.setenv("MOCK_ERP_URL", f"http://127.0.0.1:{_free_port()}")
    monkeypatch.setenv("MOCK_ERP_PASSWORD", "admin123")
    get_settings.cache_clear()
    unavailable = asyncio.run(query_order("10001"))

    assert unavailable.success is False
    assert unavailable.error_code == "ERP_UNAVAILABLE"
    assert "服务已启动" in unavailable.message
