"""Tests for data models."""

import pytest

from src.models import Item, Invoice, Relationship, CypherQuery


class TestItem:
    """Test Item dataclass."""

    def test_item_creation(self):
        """Test creating an Item."""
        item = Item(
            name="Widget",
            quantity=5,
            unit_price=10.0,
            total=50.0,
        )
        assert item.name == "Widget"
        assert item.quantity == 5
        assert item.unit_price == 10.0
        assert item.total == 50.0


class TestInvoice:
    """Test Invoice dataclass."""

    def test_invoice_creation(self):
        """Test creating an Invoice."""
        item = Item(name="Service", quantity=1, unit_price=100.0, total=100.0)
        invoice = Invoice(
            invoice_number="INV-001",
            invoice_address="123 Main St",
            date="2024-11-16",
            billed_to="ACME Corp",
            item=[item],
            subtotal=100.0,
            currency="USD",
            tax=10.0,
            tax_percentage=10.0,
            total=110.0,
        )
        assert invoice.invoice_number == "INV-001"
        assert len(invoice.item) == 1


class TestRelationship:
    """Test Relationship dataclass."""

    def test_relationship_creation(self):
        """Test creating a Relationship."""
        rel = Relationship(
            subject="Invoice-001",
            predicate="has_currency",
            object="USD",
        )
        assert rel.subject == "Invoice-001"
        assert rel.predicate == "has_currency"
        assert rel.object == "USD"


class TestCypherQuery:
    """Test CypherQuery dataclass."""

    def test_cypher_query_creation(self):
        """Test creating a CypherQuery."""
        query = CypherQuery(query="MATCH (n) RETURN n LIMIT 10")
        assert "MATCH" in query.query


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
