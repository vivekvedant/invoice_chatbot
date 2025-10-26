from dataclasses import dataclass,field


@dataclass
class Item:
    name: str = field(metadata={"description": "Name of the item"})
    quantity: int =  field(metadata={"description": "Quantity of the item"})
    unit_price: float = field(metadata={"description": "Unit  of the item"})
    total: float  = field(metadata={"description": "Total price"})

@dataclass
class Invoice:
    """Invoice Details"""
    invoice_number: str = field(metadata={"description":"Unique invoice number"})
    invoice_address: str = field(metadata={"description": "customer address"})
    date: str = field(metadata={"description": "bill Date"})
    billed_to: str = field(metadata={"description": "Name of the customer"})
    item: list[Item] =  field(metadata={"description": "List of items"})
    subtotal: float = field(metadata={"description": "Invoice Subtotal"})
    currency: str = field(metadata={"description": "Invoice Currency"})
    tax: float = field(metadata={"description": "Paid Tax"})
    tax_percentage: float = field(metadata={"description": "Tax percentage"})
    total: float = field(metadata={"description": "Total bill amount"})


@dataclass
class Relationship:
    """
    Describe a relationship between two entities.
    Subject and object should be concepts related to invoice like `Address`, `currency`, `total`, `item name`, `item price`, `item quantity` etc
    """

    subject: str
    predicate: str
    object: str


@dataclass
class CypherQuery:
    """
    Neo4j Cypher query
    """
    query:str
