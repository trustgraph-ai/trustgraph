
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.

Supports both inline document data and fetching from librarian via Pulsar
for large documents.
"""

import logging
import pytesseract
from pdf2image import convert_from_bytes

from ... base import DocumentDecoderBase

logger = logging.getLogger(__name__)

default_ident = "document-decoder"


class Processor(DocumentDecoderBase):

    COMPONENT_NAME = "tesseract-ocr-decoder"
    COMPONENT_VERSION = "1.0.0"

    def __init__(self, **params):
        super(Processor, self).__init__(**params)
        logger.info("PDF OCR processor initialized")

    def decode_pages(self, blob, mime_type=None):

        if not blob or b"%PDF-" not in blob[:1024]:
            preview = blob[:16] if blob else b""
            raise ValueError(
                f"Invalid PDF content: missing %PDF- header (starts with {preview!r})"
            )

        pages = convert_from_bytes(blob)

        for ix, page in enumerate(pages):
            page_num = ix + 1

            try:
                text = pytesseract.image_to_string(page, lang='eng')
            except Exception as e:
                logger.warning(f"Page {page_num} did not OCR: {e}")
                continue

            if text and text.strip():
                yield (text, page_num, "text")


def run():

    Processor.launch(default_ident, __doc__)
