import dataclasses


@dataclasses.dataclass
class Item:
    name: str
    quantity: int
    unit_price: float
    total: float

@dataclasses.dataclass
class Invoice:
    """Invoice Details"""

    invoice_number: str
    invoice_address: str
    date: str
    billed_to: str
    item: list[Item]
    subtotal: float
    currency: str
    tax: float
    tax_percentage: float
    total: float


