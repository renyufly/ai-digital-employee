"""Small sqlite3 data-access layer for the mock ERP."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def _connect(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(database_path: Path) -> None:
    """Create the sole orders table when it does not already exist."""
    with _connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_no TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                shipping_company TEXT,
                tracking_number TEXT,
                created_at TEXT,
                shipped_at TEXT
            )
            """
        )


def replace_orders(database_path: Path, orders: list[dict[str, Any]]) -> None:
    """Replace all rows atomically so repeated seeds stay deterministic."""
    initialize_database(database_path)
    with _connect(database_path) as connection:
        connection.execute("DELETE FROM orders")
        connection.execute("DELETE FROM sqlite_sequence WHERE name = 'orders'")
        connection.executemany(
            """
            INSERT INTO orders (
                order_no, customer_name, amount, status, shipping_company,
                tracking_number, created_at, shipped_at
            ) VALUES (
                :order_no, :customer_name, :amount, :status, :shipping_company,
                :tracking_number, :created_at, :shipped_at
            )
            """,
            orders,
        )


def get_order(database_path: Path, order_no: str) -> dict[str, Any] | None:
    """Return one order by its exact order number."""
    initialize_database(database_path)
    with _connect(database_path) as connection:
        row = connection.execute(
            "SELECT * FROM orders WHERE order_no = ?", (order_no,)
        ).fetchone()
    return dict(row) if row else None


def list_orders(database_path: Path, order_no: str | None = None) -> list[dict[str, Any]]:
    """List all orders, or filter by exact order number when supplied."""
    initialize_database(database_path)
    query = "SELECT * FROM orders"
    parameters: tuple[str, ...] = ()
    if order_no:
        query += " WHERE order_no = ?"
        parameters = (order_no,)
    query += " ORDER BY order_no"
    with _connect(database_path) as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [dict(row) for row in rows]
