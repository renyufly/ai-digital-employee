"""Deterministic sample orders for the mock ERP."""

from pathlib import Path
from typing import Any

from mock_erp.database import replace_orders


ORDERS: list[dict[str, Any]] = [
    {"order_no": "10001", "customer_name": "张三", "amount": 1280.0, "status": "已发货", "shipping_company": "顺丰", "tracking_number": "SF123456789", "created_at": "2026-08-17 09:30", "shipped_at": "2026-08-18 13:20"},
    {"order_no": "10002", "customer_name": "李四", "amount": 399.0, "status": "处理中", "shipping_company": None, "tracking_number": None, "created_at": "2026-08-19 10:15", "shipped_at": None},
    {"order_no": "10003", "customer_name": "王五", "amount": 2599.0, "status": "已完成", "shipping_company": "京东物流", "tracking_number": "JD20260618003", "created_at": "2026-06-15 14:00", "shipped_at": "2026-06-16 08:45"},
    {"order_no": "10004", "customer_name": "赵敏", "amount": 89.9, "status": "已退款", "shipping_company": None, "tracking_number": None, "created_at": "2026-08-05 11:20", "shipped_at": None},
    {"order_no": "10005", "customer_name": "陈晨", "amount": 560.0, "status": "待付款", "shipping_company": None, "tracking_number": None, "created_at": "2026-08-19 12:08", "shipped_at": None},
    {"order_no": "10006", "customer_name": "刘洋", "amount": 799.0, "status": "已取消", "shipping_company": None, "tracking_number": None, "created_at": "2026-08-14 16:40", "shipped_at": None},
    {"order_no": "10007", "customer_name": "孙悦", "amount": 1699.0, "status": "已发货", "shipping_company": "中通", "tracking_number": "ZT20260817007", "created_at": "2026-08-16 18:22", "shipped_at": "2026-08-17 09:10"},
    {"order_no": "10008", "customer_name": "周航", "amount": 219.0, "status": "已完成", "shipping_company": "圆通", "tracking_number": "YT20260725008", "created_at": "2026-07-24 08:50", "shipped_at": "2026-07-25 15:30"},
    {"order_no": "10009", "customer_name": "吴桐", "amount": 349.5, "status": "处理中", "shipping_company": None, "tracking_number": None, "created_at": "2026-08-19 08:05", "shipped_at": None},
    {"order_no": "10010", "customer_name": "郑楠", "amount": 68.0, "status": "待付款", "shipping_company": None, "tracking_number": None, "created_at": "2026-08-19 13:25", "shipped_at": None},
    {"order_no": "10011", "customer_name": "冯雪", "amount": 1024.0, "status": "已发货", "shipping_company": "顺丰", "tracking_number": "SF20260818011", "created_at": "2026-08-17 20:10", "shipped_at": "2026-08-18 11:40"},
    {"order_no": "10012", "customer_name": "蒋欣", "amount": 458.0, "status": "已退款", "shipping_company": "申通", "tracking_number": "ST20260801012", "created_at": "2026-07-31 15:35", "shipped_at": "2026-08-01 10:20"},
    {"order_no": "10013", "customer_name": "沈一", "amount": 188.0, "status": "已完成", "shipping_company": "韵达", "tracking_number": "YD20260712013", "created_at": "2026-07-11 09:12", "shipped_at": "2026-07-12 14:05"},
    {"order_no": "10014", "customer_name": "韩梅", "amount": 3200.0, "status": "处理中", "shipping_company": None, "tracking_number": None, "created_at": "2026-08-18 17:45", "shipped_at": None},
    {"order_no": "10015", "customer_name": "杨帆", "amount": 75.5, "status": "已取消", "shipping_company": None, "tracking_number": None, "created_at": "2026-08-10 10:30", "shipped_at": None},
    {"order_no": "10016", "customer_name": "朱琳", "amount": 920.0, "status": "已发货", "shipping_company": "京东物流", "tracking_number": "JD20260818016", "created_at": "2026-08-17 12:55", "shipped_at": "2026-08-18 08:15"},
    {"order_no": "10017", "customer_name": "秦朗", "amount": 149.0, "status": "待付款", "shipping_company": None, "tracking_number": None, "created_at": "2026-08-19 15:00", "shipped_at": None},
    {"order_no": "10018", "customer_name": "许诺", "amount": 678.0, "status": "已完成", "shipping_company": "中通", "tracking_number": "ZT20260730018", "created_at": "2026-07-29 13:18", "shipped_at": "2026-07-30 16:42"},
    {"order_no": "10019", "customer_name": "何安", "amount": 45.0, "status": "处理中", "shipping_company": None, "tracking_number": None, "created_at": "2026-08-19 16:16", "shipped_at": None},
    {"order_no": "10020", "customer_name": "高远", "amount": 1888.0, "status": "已发货", "shipping_company": "顺丰", "tracking_number": "SF20260819020", "created_at": "2026-08-18 09:40", "shipped_at": "2026-08-19 07:50"},
]


def seed_database(database_path: Path) -> int:
    """Reset the database to exactly the fixed sample dataset."""
    replace_orders(database_path, ORDERS)
    return len(ORDERS)
