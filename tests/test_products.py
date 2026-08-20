from fastapi.testclient import TestClient


def test_product_can_be_created_and_retrieved(client: TestClient) -> None:
    create_response = client.post(
        "/products",
        json={"name": "Mechanical Keyboard", "stock": 7},
    )

    assert create_response.status_code == 201
    product = create_response.json()
    assert product["name"] == "Mechanical Keyboard"
    assert product["stock"] == 7

    get_response = client.get(f"/products/{product['id']}")
    assert get_response.status_code == 200
    assert get_response.json() == product
