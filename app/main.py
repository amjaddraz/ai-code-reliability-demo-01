"""FastAPI application and HTTP endpoints."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Product
from app.schemas import (
    HealthResponse,
    OrderCreate,
    OrderRead,
    ProductCreate,
    ProductRead,
)
from app.services.orders import (
    IdempotencyConflictError,
    InsufficientStockError,
    ProductNotFoundError,
    create_order,
    list_orders,
)


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.post(
    "/products",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
)
def create_product(payload: ProductCreate, session: Session = Depends(get_db)) -> Product:
    product = Product(name=payload.name, stock=payload.stock)
    session.add(product)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this name already exists",
        ) from exc
    session.refresh(product)
    return product


@router.get("/products/{product_id}", response_model=ProductRead)
def get_product(product_id: int, session: Session = Depends(get_db)) -> Product:
    product = session.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product


@router.get("/products", response_model=list[ProductRead])
def get_products(session: Session = Depends(get_db)) -> list[Product]:
    return list(session.scalars(select(Product).order_by(Product.id)))


@router.post(
    "/orders",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
)
def post_order(payload: OrderCreate, session: Session = Depends(get_db)) -> Order:
    try:
        return create_order(session, payload)
    except ProductNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        ) from exc
    except InsufficientStockError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Insufficient stock",
        ) from exc
    except IdempotencyConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="client_request_id already used with different order data",
        ) from exc


@router.get("/orders", response_model=list[OrderRead])
def get_orders(session: Session = Depends(get_db)) -> list[Order]:
    return list_orders(session)


def create_app(*, initialize_database: bool = True) -> FastAPI:
    """Build the application, optionally initializing its default database."""

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if initialize_database:
            Base.metadata.create_all(bind=engine)
        yield

    application = FastAPI(
        title="Order Reliability Demonstration",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.include_router(router)
    return application


app = create_app()
