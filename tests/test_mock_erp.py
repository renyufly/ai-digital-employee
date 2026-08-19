import asyncio
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from mock_erp.app import create_app
from mock_erp.database import get_order, list_orders
from mock_erp.seed import seed_database


def test_seed_is_deterministic(tmp_path: Path) -> None:
    database_path = tmp_path / "orders.db"
    assert seed_database(database_path) == 20
    assert seed_database(database_path) == 20

    orders = list_orders(database_path)
    assert len(orders) == 20
    assert len({order["order_no"] for order in orders}) == 20
    assert get_order(database_path, "10001") == {
        "id": 1,
        "order_no": "10001",
        "customer_name": "张三",
        "amount": 1280.0,
        "status": "已发货",
        "shipping_company": "顺丰",
        "tracking_number": "SF123456789",
        "created_at": "2026-08-17 09:30",
        "shipped_at": "2026-08-18 13:20",
    }


def test_login_search_and_order_detail(tmp_path: Path) -> None:
    async def scenario() -> None:
        database_path = tmp_path / "orders.db"
        seed_database(database_path)
        app = create_app(database_path, "admin", "admin123", "test-secret")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            protected = await client.get("/orders", follow_redirects=False)
            assert protected.status_code == 303
            assert protected.headers["location"] == "/login"

            failed = await client.post(
                "/login", data={"username": "admin", "password": "wrong"}
            )
            assert failed.status_code == 401
            assert "用户名或密码错误" in failed.text

            login = await client.post(
                "/login",
                data={"username": "admin", "password": "admin123"},
                follow_redirects=False,
            )
            assert login.status_code == 303
            assert login.headers["location"] == "/orders"

            results = await client.get("/orders", params={"order_no": "10001"})
            assert results.status_code == 200
            assert 'data-testid="order-row-10001"' in results.text
            assert "SF123456789" in results.text

            detail = await client.get("/orders/10001")
            assert detail.status_code == 200
            assert 'data-testid="status">已发货' in detail.text
            assert 'data-testid="shipping-company">顺丰' in detail.text
            assert 'data-testid="tracking-number">SF123456789' in detail.text

            missing = await client.get("/orders", params={"order_no": "99999"})
            assert missing.status_code == 200
            assert "未找到订单 99999" in missing.text

            empty = await client.get("/orders?order_no=")
            assert empty.status_code == 200
            assert "请输入订单号" in empty.text

    asyncio.run(scenario())
