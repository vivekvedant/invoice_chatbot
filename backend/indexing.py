import dataclasses
import cocoindex
from docling.document_converter import DocumentConverter

import tempfile
import dataclasses
import os
from dotenv import load_dotenv

load_dotenv()


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
            
            result =self._converter.convert(temp_file.name)
            markdown = result.document.export_to_markdown()
            return markdown





@cocoindex.flow_def(name="invoice_kg")
def docs_to_kg_flow(
    flow_builder: cocoindex.FlowBuilder, data_scope: cocoindex.DataScope
) -> None:
    """
    """
    data_scope["documents"] = flow_builder.add_source(
        cocoindex.sources.LocalFile(path="invoices", binary=True)
    )

    with data_scope["documents"].row() as doc:
        
        # convert invoice to markdown
        doc["markdown"] = doc["content"].transform(PdfToMarkdown())
        



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
