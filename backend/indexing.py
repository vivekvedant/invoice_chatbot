import dataclasses
import cocoindex
from docling.document_converter import DocumentConverter

import tempfile
import dataclasses
import os
from dotenv import load_dotenv
from models import Invoice, Relationship, CypherQuery
from neo4j import GraphDatabase


load_dotenv()

os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")


class PdfToMarkdown(cocoindex.op.FunctionSpec):
    """Convert a PDF to markdown."""


@cocoindex.op.executor_class(gpu=True, cache=True, behavior_version=1)
class PdfToMarkdownExecutor:
    """Executor for PdfToMarkdown."""

    spec: PdfToMarkdown
    _converter = DocumentConverter()

    def __call__(self, content: bytes) -> str:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_file:
            temp_file.write(content)
            temp_file.flush()

            result = self._converter.convert(temp_file.name)
            markdown = result.document.export_to_markdown()
            return markdown


class Neo4jTarget(cocoindex.op.TargetSpec):
    neo4j_uri: str
    user: str
    password: str


@cocoindex.op.target_connector(spec_cls=Neo4jTarget)
class Neo4JTargetConnector:
    @staticmethod
    def get_persistent_key(spec: Neo4jTarget, target_name: str) -> str:
        return spec.neo4j_uri

    @staticmethod
    def describe(key: str) -> str:
        return

    @staticmethod
    def apply_setup_change(key, previous, current) -> None:
        return

    @staticmethod
    def mutate(*all_mutations: tuple[Neo4jTarget, dict[str, dict | None]]):
        for spec, mutations in all_mutations:
            if not mutations:
                continue
            driver = GraphDatabase.driver(
                spec.neo4j_uri, auth=(spec.user, spec.password)
            )
            cypher_query = """
                MERGE (inv:Invoice {{invoice_number:{invoice_no}}})
                SET inv.filename = "{filename}",
                    inv.invoice_address = "{invoice_address}",
                    inv.date = "{invoice_date}",
                    inv.billed_to = "{billed_to}",
                    inv.subtotal = {subtotal},
                    inv.currency = "{currency}",
                    inv.tax = {tax},
                    inv.tax_percentage = {tax_percentage},
                    inv.total = {total}

                WITH inv,{item} AS items

                UNWIND items AS item_data
                MERGE (i:Item {{name: item_data.name}})
                SET i.quantity = item_data.quantity,
                    i.unit_price = item_data.unit_price,
                    i.total = item_data.total
                MERGE (inv)-[:HAS_ITEM]->(i)

                RETURN inv, collect(i) AS items;

                """

            for filename_key, value in mutations.items():
                if value is None:
                    continue

                invoice_data = value['invoice_details']

                params = {
                    "invoice_no": invoice_data.get("invoice_number"),
                    "filename": value.get("filename", filename_key),
                    "invoice_address": invoice_data.get("invoice_address"),
                    "invoice_date": invoice_data.get("date"),
                    "billed_to": invoice_data.get("billed_to"),
                    "subtotal": invoice_data.get("subtotal"),
                    "currency": invoice_data.get("currency"),
                    "tax": invoice_data.get("tax"),
                    "tax_percentage": invoice_data.get("tax_percentage"),
                    "total": invoice_data.get("total"),
                    "items": invoice_data.get("item", []),
                }

                cypher_query = """
                MERGE (inv:Invoice {invoice_number: $invoice_no})
                SET inv.filename = $filename,
                    inv.invoice_address = $invoice_address,
                    inv.date = $invoice_date,
                    inv.billed_to = $billed_to,
                    inv.subtotal = $subtotal,
                    inv.currency = $currency,
                    inv.tax = $tax,
                    inv.tax_percentage = $tax_percentage,
                    inv.total = $total

                WITH inv, $items AS items
                UNWIND items AS item_data
                MERGE (i:Item {name: item_data.name})
                SET i.quantity = item_data.quantity,
                    i.unit_price = item_data.unit_price,
                    i.total = item_data.total
                MERGE (inv)-[:HAS_ITEM]->(i)
                RETURN inv, collect(i) AS items
                """

                with driver.session() as session:
                    session.run(cypher_query, params)


@cocoindex.flow_def(name="invoice_kg_v8")
def docs_to_kg_flow(
    flow_builder: cocoindex.FlowBuilder, data_scope: cocoindex.DataScope
) -> None:
    """ """
    data_scope["documents"] = flow_builder.add_source(
        cocoindex.sources.LocalFile(path="invoices", binary=True)
    )

    document_node = data_scope.add_collector()
    # entity_relationship = data_scope.add_collector()
    # entity_mention = data_scope.add_collector()

    with data_scope["documents"].row() as doc:

        # convert invoice to markdown
        doc["markdown"] = doc["content"].transform(PdfToMarkdown())

        # extracting invoice details
        doc["invoice_details"] = doc["markdown"].transform(
            cocoindex.functions.ExtractByLlm(
                llm_spec=cocoindex.LlmSpec(
                    api_type=cocoindex.LlmApiType.GEMINI,
                    model="gemini-flash-lite-latest",
                ),
                output_type=Invoice,
                instruction="Extract invoice details",
            )
        )

        document_node.collect(
            filename=doc["filename"],
            invoice_details = doc['invoice_details'],
            invoice_number=doc["invoice_details"]["invoice_number"],
        )

        document_node.export(
            "Neo4jKnowledgeGraph",
            Neo4jTarget(
                neo4j_uri=os.getenv("NEO4J_URI"),
                user=os.getenv("NEO4J_USER"),
                password=os.getenv("NEO4J_PASSWORD"),
            ),
            primary_key_fields=["invoice_number"],
        )


def main():

    # Setup the flow
    docs_to_kg_flow.setup(report_to_stdout=True)

    try:
        with cocoindex.FlowLiveUpdater(
            docs_to_kg_flow, cocoindex.FlowLiveUpdaterOptions(print_stats=True)
        ) as updater:
            print("Live updater started. Press Ctrl+C to stop.")
            updates = updater.next_status_updates()
            if not updates.active_sources:
                print("All sources have finished processing.")
            else:
                for source_name in updates.updated_sources:
                    print(f"Source '{source_name}' has been updated.")
            updater.wait()
    except Exception as e:
        print(f"Error occurred: {e}")


if __name__ == "__main__":
    cocoindex.init()
    main()
