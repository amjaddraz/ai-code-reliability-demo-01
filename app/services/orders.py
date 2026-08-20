"""Order creation business logic."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Order, Product
from app.schemas import OrderCreate


class ProductNotFoundError(Exception):
    """Raised when an order references an unknown product."""


class InsufficientStockError(Exception):
    """Raised when a product cannot fulfill an order."""


def create_order(session: Session, request: OrderCreate) -> Order:
    """Create an order and reserve its inventory in one transaction."""

    product = session.get(Product, request.product_id)
    if product is None:
        raise ProductNotFoundError

    if product.stock < request.quantity:
        raise InsufficientStockError

    product.stock -= request.quantity
    order = Order(
        client_request_id=request.client_request_id,
        product_id=request.product_id,
        quantity=request.quantity,
    )
    session.add(order)
    session.flush()

    prior_order = session.scalar(
        select(Order)
        .where(
            Order.client_request_id == request.client_request_id,
            Order.id != order.id,
        )
        .order_by(Order.id)
        .limit(1)
    )

    session.commit()

    if prior_order is not None:
        session.refresh(prior_order)
        return prior_order

    session.refresh(order)
    return order


def list_orders(session: Session) -> list[Order]:
    """Return orders in creation order."""

    return list(session.scalars(select(Order).order_by(Order.id)))
