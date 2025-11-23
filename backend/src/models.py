from dataclasses import dataclass, field

@dataclass
class Item:
    """A single line item on an invoice.

    User-facing note: `total` is expected to equal `quantity * unit_price`.
    """

    name: str = field(metadata={"description": "Name of the item"})
    quantity: int = field(metadata={"description": "Quantity of the item"})
    unit_price: float = field(metadata={"description": "Unit price of the item"})
    total: float = field(metadata={"description": "Total price"})


@dataclass
class Invoice:
    """Invoice data extracted from a PDF.

    Keep fields lightweight and serializable so they can be saved into the
    knowledge graph or used to generate a short summary for users.
    """

    invoice_number: str = field(metadata={"description": "Unique invoice number"})
    invoice_address: str = field(metadata={"description": "Invoice address"})
    date: str = field(metadata={"description": "Bill date"})
    billed_to: str = field(metadata={"description": "Name of the customer"})
    item: list[Item] = field(metadata={"description": "List of items"})
    subtotal: float = field(metadata={"description": "Invoice subtotal"})
    currency: str = field(metadata={"description": "Invoice currency"})
    tax: float = field(metadata={"description": "Paid tax"})
    tax_percentage: float = field(metadata={"description": "Tax percentage"})
    total: float = field(metadata={"description": "Total bill amount"})


@dataclass
class Relationship:
    """A simple knowledge-graph edge between two concepts.

    Example: Relationship(subject="Invoice123", predicate="HAS_TOTAL", object="$100.00")
    """

    subject: str
    predicate: str
    object: str


@dataclass
class CypherQuery:
    """
    A Neo4j Cypher query.

    Attributes:
        query: The Cypher query string.
    """

    query: str
