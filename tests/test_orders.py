import pytest
from fastapi.testclient import TestClient


def test_normal_order_creation(client: TestClient, product: dict[str, object]) -> None:
    response = client.post(
        "/orders",
        json={
            "client_request_id": "request-001",
            "product_id": product["id"],
            "quantity": 3,
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "client_request_id": "request-001",
        "product_id": product["id"],
        "quantity": 3,
    }


def test_stock_decreases_after_order(client: TestClient, product: dict[str, object]) -> None:
    response = client.post(
        "/orders",
        json={
            "client_request_id": "request-002",
            "product_id": product["id"],
            "quantity": 4,
        },
    )
    assert response.status_code == 201

    product_response = client.get(f"/products/{product['id']}")
    assert product_response.status_code == 200
    assert product_response.json()["stock"] == 6


def test_repeated_client_request_does_not_create_duplicate_order(
    client: TestClient,
    product: dict[str, object],
) -> None:
    payload = {
        "client_request_id": "request-retry-001",
        "product_id": product["id"],
        "quantity": 2,
    }

    first_response = client.post("/orders", json=payload)
    second_response = client.post("/orders", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert second_response.json()["id"] == first_response.json()["id"]

    orders_response = client.get("/orders")
    product_response = client.get(f"/products/{product['id']}")

    assert orders_response.status_code == 200
    assert len(orders_response.json()) == 1
    assert product_response.status_code == 200
    assert product_response.json()["stock"] == 8


def test_exact_retry_succeeds_after_inventory_is_exhausted(
    client: TestClient,
) -> None:
    product_response = client.post(
        "/products",
        json={"name": "Limited Lamp", "stock": 2},
    )
    assert product_response.status_code == 201
    product = product_response.json()
    payload = {
        "client_request_id": "request-exhausted-retry-001",
        "product_id": product["id"],
        "quantity": 2,
    }

    first_response = client.post("/orders", json=payload)
    assert first_response.status_code == 201
    assert client.get(f"/products/{product['id']}").json()["stock"] == 0

    retry_response = client.post("/orders", json=payload)

    assert retry_response.status_code == 201
    assert retry_response.json()["id"] == first_response.json()["id"]
    assert retry_response.json() == first_response.json()
    assert len(client.get("/orders").json()) == 1
    assert client.get(f"/products/{product['id']}").json()["stock"] == 0


@pytest.mark.parametrize(
    ("quantity", "use_different_product"),
    [(11, False), (2, True)],
    ids=["different-quantity", "different-product"],
)
def test_reused_client_request_with_different_order_data_is_rejected(
    client: TestClient,
    product: dict[str, object],
    quantity: int,
    use_different_product: bool,
) -> None:
    original_payload = {
        "client_request_id": "request-conflict-001",
        "product_id": product["id"],
        "quantity": 2,
    }
    assert client.post("/orders", json=original_payload).status_code == 201

    other_product_response = client.post(
        "/products",
        json={"name": "Floor Lamp", "stock": 10},
    )
    assert other_product_response.status_code == 201
    other_product = other_product_response.json()
    conflicting_payload = {
        **original_payload,
        "product_id": (
            other_product["id"] if use_different_product else product["id"]
        ),
        "quantity": quantity,
    }

    response = client.post("/orders", json=conflicting_payload)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "client_request_id already used with different order data"
    }
    assert len(client.get("/orders").json()) == 1
    assert client.get(f"/products/{product['id']}").json()["stock"] == 8
    assert client.get(f"/products/{other_product['id']}").json()["stock"] == 10


def test_insufficient_stock_is_rejected(
    client: TestClient,
    product: dict[str, object],
) -> None:
    response = client.post(
        "/orders",
        json={
            "client_request_id": "request-003",
            "product_id": product["id"],
            "quantity": 11,
        },
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Insufficient stock"}


def test_unknown_product_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/orders",
        json={
            "client_request_id": "request-004",
            "product_id": 999,
            "quantity": 1,
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


@pytest.mark.parametrize("quantity", [0, -1])
def test_non_positive_quantity_is_rejected(
    client: TestClient,
    product: dict[str, object],
    quantity: int,
) -> None:
    response = client.post(
        "/orders",
        json={
            "client_request_id": f"request-quantity-{quantity}",
            "product_id": product["id"],
            "quantity": quantity,
        },
    )

    assert response.status_code == 422


def test_orders_are_listed(client: TestClient, product: dict[str, object]) -> None:
    first = {
        "client_request_id": "request-005",
        "product_id": product["id"],
        "quantity": 2,
    }
    second = {
        "client_request_id": "request-006",
        "product_id": product["id"],
        "quantity": 1,
    }
    assert client.post("/orders", json=first).status_code == 201
    assert client.post("/orders", json=second).status_code == 201

    response = client.get("/orders")

    assert response.status_code == 200
    orders = response.json()
    assert len(orders) == 2
    assert [order["client_request_id"] for order in orders] == [
        "request-005",
        "request-006",
    ]
