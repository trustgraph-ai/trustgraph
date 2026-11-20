
"""
Mistral OCR decoder, accepts PDF documents on input, outputs pages from the
PDF document as markdown text as separate output objects.

Supports both inline document data and fetching from librarian via Pulsar
for large documents.
"""

from pypdf import PdfWriter, PdfReader
from io import BytesIO
import uuid
import os

from mistralai import Mistral

from ... base import DocumentDecoderBase

import logging

logger = logging.getLogger(__name__)

default_ident = "document-decoder"
default_api_key = os.getenv("MISTRAL_TOKEN")

pages_per_chunk = 5


def chunks(lst, n):
    "Yield successive n-sized chunks from lst."
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def replace_images_in_markdown(markdown_str, images_dict):
    for img_name, base64_str in images_dict.items():
        markdown_str = markdown_str.replace(
            f"![{img_name}]({img_name})", f"![{img_name}]({base64_str})"
        )
    return markdown_str


class Processor(DocumentDecoderBase):

    COMPONENT_NAME = "mistral-ocr-decoder"
    COMPONENT_VERSION = "1.0.0"

    def __init__(self, **params):

        api_key = params.get("api_key", default_api_key)

        super(Processor, self).__init__(**params)

        if api_key is None:
            raise RuntimeError("Mistral API key not specified")

        self.mistral = Mistral(api_key=api_key)
        self.unique_id = str(uuid.uuid4())

        logger.info("Mistral OCR processor initialized")

    def decode_pages(self, blob, mime_type=None):

        pdfbuf = BytesIO(blob)
        pdf = PdfReader(pdfbuf)

        global_page_num = 0

        for chunk in chunks(pdf.pages, pages_per_chunk):

            part = PdfWriter()
            for page in chunk:
                part.add_page(page)

            buf = BytesIO()
            part.write_stream(buf)

            uploaded_file = self.mistral.files.upload(
                file={
                    "file_name": self.unique_id,
                    "content": buf.getvalue(),
                },
                purpose="ocr",
            )

            signed_url = self.mistral.files.get_signed_url(
                file_id=uploaded_file.id, expiry=1
            )

            processed = self.mistral.ocr.process(
                model="mistral-ocr-latest",
                include_image_base64=True,
                document={
                    "type": "document_url",
                    "document_url": signed_url.url,
                }
            )

            for page in processed.pages:
                global_page_num += 1
                image_data = {}
                for img in page.images:
                    image_data[img.id] = img.image_base64
                markdown = replace_images_in_markdown(
                    page.markdown, image_data
                )
                if markdown and markdown.strip():
                    yield (markdown, global_page_num, "text")

        logger.info(f"OCR complete, {global_page_num} pages.")

    @staticmethod
    def add_args(parser):

        DocumentDecoderBase.add_args(parser)

        parser.add_argument(
            '-k', '--api-key',
            default=default_api_key,
            help=f'Mistral API Key'
        )


def run():

    Processor.launch(default_ident, __doc__)
