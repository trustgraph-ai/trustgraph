
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.

Supports both inline document data and streaming from librarian API
for large documents.
"""

import os
import tempfile
import base64
import logging
from langchain_community.document_loaders import PyPDFLoader

from ... schema import Document, TextDocument, Metadata
from ... base import FlowProcessor, ConsumerSpec, ProducerSpec

# Module logger
logger = logging.getLogger(__name__)

default_ident = "pdf-decoder"

# Default API URL for fetching documents from librarian
default_api_url = os.environ.get("TRUSTGRAPH_API_URL", "http://api:8088")


class Processor(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id", default_ident)

        super(Processor, self).__init__(
            **params | {
                "id": id,
            }
        )

        self.api_url = params.get("api_url", default_api_url)

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = Document,
                handler = self.on_message,
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "output",
                schema = TextDocument,
            )
        )

        logger.info("PDF decoder initialized")

    def _fetch_document_to_file(self, document_id, user, file_path, chunk_size=1024*1024):
        """
        Fetch document content from librarian API and stream to file.

        This avoids loading the entire document into memory at once.
        """
        import requests

        logger.info(f"Streaming document {document_id} to temp file...")

        # Use chunk-based streaming to minimize memory usage
        chunk_index = 0
        total_bytes = 0

        with open(file_path, 'wb') as f:
            while True:
                url = f"{self.api_url}/api/v1/librarian"
                payload = {
                    "operation": "stream-document",
                    "user": user,
                    "document-id": document_id,
                    "chunk-index": chunk_index,
                    "chunk-size": chunk_size,
                }

                try:
                    response = requests.post(url, json=payload, timeout=60)
                    response.raise_for_status()
                    data = response.json()
                except requests.RequestException as e:
                    logger.error(f"Failed to fetch chunk {chunk_index}: {e}")
                    raise

                if "error" in data and data["error"]:
                    raise RuntimeError(f"API error: {data['error']}")

                content_b64 = data.get("content", "")
                if not content_b64:
                    break

                chunk_data = base64.b64decode(content_b64)
                f.write(chunk_data)
                total_bytes += len(chunk_data)

                total_chunks = data.get("total-chunks", 1)
                if chunk_index >= total_chunks - 1:
                    break

                chunk_index += 1

        logger.info(f"Downloaded {total_bytes} bytes to temp file")
        return total_bytes

    async def on_message(self, msg, consumer, flow):

        logger.debug("PDF message received")

        v = msg.value()

        logger.info(f"Decoding PDF {v.metadata.id}...")

        with tempfile.NamedTemporaryFile(delete_on_close=False, suffix='.pdf') as fp:
            temp_path = fp.name

            # Check if we should fetch from librarian or use inline data
            if v.document_id:
                # Stream from librarian API to temp file
                logger.info(f"Fetching document {v.document_id} from librarian...")
                fp.close()
                self._fetch_document_to_file(
                    document_id=v.document_id,
                    user=v.metadata.user,
                    file_path=temp_path,
                )
            else:
                # Use inline data (backward compatibility)
                fp.write(base64.b64decode(v.data))
                fp.close()

            loader = PyPDFLoader(temp_path)
            pages = loader.load()

            for ix, page in enumerate(pages):

                logger.debug(f"Processing page {ix}")

                r = TextDocument(
                    metadata=v.metadata,
                    text=page.page_content.encode("utf-8"),
                )

                await flow("output").send(r)

        # Clean up temp file
        try:
            os.unlink(temp_path)
        except OSError:
            pass

        logger.debug("PDF decoding complete")

    @staticmethod
    def add_args(parser):
        FlowProcessor.add_args(parser)

        parser.add_argument(
            '--api-url',
            default=default_api_url,
            help=f'TrustGraph API URL for document streaming (default: {default_api_url})',
        )

def run():

    Processor.launch(default_ident, __doc__)

