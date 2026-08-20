"""API request and response schemas."""

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    stock: int = Field(ge=0)


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    stock: int


class OrderCreate(BaseModel):
    client_request_id: str = Field(min_length=1, max_length=120)
    product_id: int
    quantity: int = Field(gt=0)


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_request_id: str
    product_id: int
    quantity: int
