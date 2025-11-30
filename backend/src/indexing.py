import os
import tempfile

import boto3
import cocoindex
from docling.document_converter import DocumentConverter
from dotenv import load_dotenv
from neo4j import GraphDatabase
from models import Invoice
from cache_manager import CacheManager
from logging_config import get_indexer_logger
from cocoindex.setting import ServerSettings
from cocoindex import start_server

load_dotenv(dotenv_path=".env")

dynamodb = boto3.resource("dynamodb")

logger = get_indexer_logger()


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


@cocoindex.op.function()
def update_database(filename: str, status: str) -> str:
    """Update file indexing status in cache and database."""
    try:
        cache_manager = CacheManager()
        cache_manager.update_cache_and_database(
            file_name=filename, indexing_status=status
        )
        logger.info(f"Updated indexing status: {filename} → {status}")
        return "completed"
    except Exception as e:
        logger.error(
            f"Failed to update database for {filename}: {str(e)}", exc_info=True
        )
        return "failed"


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
        return key

    @staticmethod
    def apply_setup_change(key, previous, current) -> None:
        return

    @staticmethod
    def mutate(*all_mutations: tuple[Neo4jTarget, dict[str, dict | None]]):
        for spec, mutations in all_mutations:
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
                    params = {"invoice_number": filename_key}
                    cypher_query = """
                    MATCH (i:Invoice {invoice_number: $invoice_number})-[*0..]-(n)
                    DETACH DELETE i, n;

                    """
                    with driver.session() as session:
                        session.run(cypher_query, params)

                    logger.info(f"Deleted Neo4j records for invoice: {filename_key}")
                    break

                invoice_data = value["invoice_details"]

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
                    invoice_num = invoice_data.get("invoice_number")
                    logger.info(f"Persisted invoice to Neo4j: {invoice_num}")


@cocoindex.flow_def(name="invoice_kg")
def invoice_to_kg(
    flow_builder: cocoindex.FlowBuilder, data_scope: cocoindex.DataScope
) -> None:
    """Define invoice knowledge graph processing flow."""
    bucket_name = os.environ["AMAZON_S3_BUCKET_NAME"]
    prefix = os.environ.get("AMAZON_S3_PREFIX", None)
    sqs_queue_url = os.environ.get("AMAZON_S3_SQS_QUEUE_URL", None)

    logger.info(f"Starting flow: bucket={bucket_name}, prefix={prefix}")

    data_scope["documents"] = flow_builder.add_source(
        cocoindex.sources.AmazonS3(
            bucket_name=bucket_name,
            prefix=prefix,
            included_patterns=[
                "*.pdf",
            ],
            binary=True,
            sqs_queue_url=sqs_queue_url,
        )
    )

    document_node = data_scope.add_collector()

    with data_scope["documents"].row() as doc:

        doc["file_indexing"] = doc["filename"].transform(
            update_database, status="indexing"
        )

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
            invoice_details=doc["invoice_details"],
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

        doc["file_indexing_completed"] = doc["filename"].transform(
            update_database, status="completed"
        )


def main():
    """Start the indexing service."""
    logger.info("Indexing service initialized")

    cocoindex.init()

    server_settings = ServerSettings(
        address="127.0.0.1:49344",
        cors_origins=["https://cocoindex.io"],
    )

    start_server(server_settings)
    try:

        # Setup the flow
        invoice_to_kg.setup(report_to_stdout=True)

        with cocoindex.FlowLiveUpdater(
            invoice_to_kg, cocoindex.FlowLiveUpdaterOptions(print_stats=True)
        ) as updater:
            logger.info("Live updater started. Listening for documents...")
            try:
                updater.wait()
            except KeyboardInterrupt:
                logger.info("Indexing service interrupted by user")
    except Exception as e:
        logger.error(f"Indexing service error: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
