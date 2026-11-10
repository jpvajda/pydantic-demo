from pydantic import BaseModel, Field


class Order(BaseModel):
    order_id: str = Field(min_length=1)
    user_id: int = Field(ge=1)
    sku: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    unit_price: float = Field(gt=0)


class EnrichedOrder(Order):
    customer_name: str
    customer_email: str
