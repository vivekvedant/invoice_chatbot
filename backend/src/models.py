"""
Data models for invoice processing and Neo4j relationships.

Defines Pydantic/dataclass models for invoice structure, line items,
and knowledge graph relationships.
"""

from dataclasses import dataclass, field


@dataclass
class Item:
    """
    A line item within an invoice.

    Attributes:
        name: Description of the item.
        quantity: Number of units.
        unit_price: Price per unit.
        total: Total price for this line item.
    """

    name: str = field(metadata={"description": "Name of the item"})
    quantity: int = field(metadata={"description": "Quantity of the item"})
    unit_price: float = field(metadata={"description": "Unit price of the item"})
    total: float = field(metadata={"description": "Total price"})


@dataclass
class Invoice:
    """
    Invoice details extracted from PDF document.

    Attributes:
        invoice_number: Unique invoice identifier.
        invoice_address: Invoice address.
        date: Bill date.
        billed_to: Customer name.
        item: List of line items.
        subtotal: Sum before tax.
        currency: Currency code or symbol.
        tax: Tax amount.
        tax_percentage: Tax rate as percentage.
        total: Final total including tax.
    """

    invoice_number: str = field(
        metadata={"description": "Unique invoice number"}
    )
    invoice_address: str = field(
        metadata={"description": "Invoice address"}
    )
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
    """
    Represent a relationship between two entities in the knowledge graph.

    Subject and object should be concepts extracted from invoices, such as:
    Address, Currency, Total, Item Name, Item Price, Item Quantity, etc.

    Attributes:
        subject: First entity.
        predicate: Relationship type.
        object: Second entity.
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
