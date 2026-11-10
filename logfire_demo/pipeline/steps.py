import json
import sqlite3
import time
from pathlib import Path

import httpx
import logfire
from pydantic import ValidationError

from pipeline.models import EnrichedOrder, Order

JSONPLACEHOLDER = "https://jsonplaceholder.typicode.com"
SLOW_ORDER_ID = "ORD-SLOW"
SLOW_SECONDS = 1.2


def load(path: Path) -> list[dict]:
    with path.open() as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON list of orders")
    return payload


def validate(raw_orders: list[dict]) -> tuple[list[Order], list[str]]:
    valid: list[Order] = []
    errors: list[str] = []
    for raw in raw_orders:
        label = raw.get("order_id", "<missing order_id>") if isinstance(raw, dict) else "<not an object>"
        try:
            valid.append(Order.model_validate(raw))
        except ValidationError as exc:
            first = exc.errors()[0]
            field = ".".join(str(part) for part in first["loc"])
            logfire.warn(
                "order {order_id} failed validation",
                order_id=str(label),
                error_count=exc.error_count(),
                field=field,
                reason=first["type"],
            )
            errors.append(f"{label}: {exc.error_count()} validation error(s)")
    return valid, errors


def enrich(orders: list[Order]) -> tuple[list[EnrichedOrder], list[str]]:
    enriched: list[EnrichedOrder] = []
    errors: list[str] = []
    with httpx.Client(base_url=JSONPLACEHOLDER, timeout=10.0) as client:
        for order in orders:
            with logfire.span(
                "enrich order {order_id}",
                order_id=order.order_id,
                user_id=order.user_id,
            ):
                if order.order_id == SLOW_ORDER_ID:
                    with logfire.span(
                        "slow enrichment delay",
                        order_id=order.order_id,
                        seconds=SLOW_SECONDS,
                    ):
                        time.sleep(SLOW_SECONDS)
                response = client.get(f"/users/{order.user_id}")
                if response.status_code == 404:
                    logfire.error(
                        "user {user_id} not found for order {order_id}",
                        user_id=order.user_id,
                        order_id=order.order_id,
                    )
                    errors.append(f"{order.order_id}: user {order.user_id} not found")
                    continue
                response.raise_for_status()
                user = response.json()
                enriched.append(
                    EnrichedOrder(
                        **order.model_dump(),
                        customer_name=user["name"],
                        customer_email=user["email"],
                    )
                )
                logfire.info(
                    "enriched order {order_id} for {customer_name}",
                    order_id=order.order_id,
                    customer_name=user["name"],
                )
    return enriched, errors


def save(orders: list[EnrichedOrder], db_path: Path) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                sku TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                customer_name TEXT NOT NULL,
                customer_email TEXT NOT NULL
            )
            """
        )
        cursor.executemany(
            """
            INSERT INTO orders (
                order_id, user_id, sku, quantity, unit_price, customer_name, customer_email
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(order_id) DO UPDATE SET
                user_id = excluded.user_id,
                sku = excluded.sku,
                quantity = excluded.quantity,
                unit_price = excluded.unit_price,
                customer_name = excluded.customer_name,
                customer_email = excluded.customer_email
            """,
            [
                (
                    order.order_id,
                    order.user_id,
                    order.sku,
                    order.quantity,
                    order.unit_price,
                    order.customer_name,
                    order.customer_email,
                )
                for order in orders
            ],
        )
    return len(orders)
