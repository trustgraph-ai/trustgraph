
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.

Supports both inline document data and fetching from librarian via Pulsar
for large documents.
"""

import os
import tempfile
import logging

from pypdf import PdfReader

from ... base import DocumentDecoderBase

logger = logging.getLogger(__name__)

default_ident = "document-decoder"


class Processor(DocumentDecoderBase):

    COMPONENT_NAME = "pdf-decoder"
    COMPONENT_VERSION = "1.0.0"

    def __init__(self, **params):
        super(Processor, self).__init__(**params)
        logger.info("PDF decoder initialized")

    def decode_pages(self, blob, mime_type=None):

        if not blob or b"%PDF-" not in blob[:1024]:
            preview = blob[:16] if blob else b""
            raise ValueError(
                f"Invalid PDF content: missing %PDF- header (starts with {preview!r})"
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as fp:
            temp_path = fp.name
            fp.write(blob)

        try:
            reader = PdfReader(temp_path)
            for ix, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    yield (text, ix + 1, "text")
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def run():

    Processor.launch(default_ident, __doc__)
