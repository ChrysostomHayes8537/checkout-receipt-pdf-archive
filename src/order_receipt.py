"""Checkout receipt workflow for a small ecommerce service."""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Order:
    order_id: str
    customer_email: str
    item_name: str
    quantity: int
    total: str


def receipt_fields(order: Order) -> dict[str, str]:
    """Map one order into the merchant's AcroForm field names."""
    return {
        "order_id": order.order_id,
        "customer_email": order.customer_email,
        "item_name": order.item_name,
        "quantity": str(order.quantity),
        "total": order.total,
        "fulfillment_status": "ready_to_ship",
    }


def fill_and_archive(
    order: Order,
    fill_pdf: Callable[[str, dict[str, str], bool], str],
    put_object: Callable[[str, str, str], str],
    template_pdf: str,
) -> dict[str, str]:
    """Flatten a receipt, archive it, and expose the customer update state."""
    flattened_pdf = fill_pdf(template_pdf, receipt_fields(order), True)
    object_key = f"receipts/{order.order_id}.pdf"
    archive_result = put_object("receipts", object_key, flattened_pdf)
    return {
        "order_id": order.order_id,
        "status": "receipt_archived",
        "fulfillment_status": "ready_to_ship",
        "archive_key": object_key,
        "archive_result": archive_result,
    }


def as_dict(order: Order) -> dict[str, Any]:
    return {
        "order_id": order.order_id,
        "customer_email": order.customer_email,
        "item_name": order.item_name,
        "quantity": order.quantity,
        "total": order.total,
    }
