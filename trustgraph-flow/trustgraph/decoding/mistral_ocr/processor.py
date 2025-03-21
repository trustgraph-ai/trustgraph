
"""
Simple decoder, accepts PDF documents on input, outputs pages from the
PDF document as text as separate output objects.
"""

from pypdf import PdfWriter, PdfReader
from io import BytesIO
import base64
import uuid
import os

from mistralai import Mistral
from mistralai import DocumentURLChunk, ImageURLChunk, TextChunk
from mistralai.models import OCRResponse

from ... schema import Document, TextDocument, Metadata
from ... schema import document_ingest_queue, text_ingest_queue
from ... log_level import LogLevel
from ... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = document_ingest_queue
default_output_queue = text_ingest_queue
default_subscriber = module
default_api_key = os.getenv("MISTRAL_TOKEN")

pages_per_chunk = 5

def chunks(lst, n):
    "Yield successive n-sized chunks from lst."
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def replace_images_in_markdown(markdown_str: str, images_dict: dict) -> str:
    """
    Replace image placeholders in markdown with base64-encoded images.

    Args:
        markdown_str: Markdown text containing image placeholders
        images_dict: Dictionary mapping image IDs to base64 strings

    Returns:
        Markdown text with images replaced by base64 data
    """
    for img_name, base64_str in images_dict.items():
        markdown_str = markdown_str.replace(
            f"![{img_name}]({img_name})", f"![{img_name}]({base64_str})"
        )
    return markdown_str

def get_combined_markdown(ocr_response: OCRResponse) -> str:
    """
    Combine OCR text and images into a single markdown document.

    Args:
        ocr_response: Response from OCR processing containing text and images

    Returns:
        Combined markdown string with embedded images
    """
    markdowns: list[str] = []
    # Extract images from page
    for page in ocr_response.pages:
        image_data = {}
        for img in page.images:
            image_data[img.id] = img.image_base64
        # Replace image placeholders with actual images
        markdowns.append(replace_images_in_markdown(page.markdown, image_data))

    return "\n\n".join(markdowns)

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        api_key = params.get("api_key", default_api_key)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "input_schema": Document,
                "output_schema": TextDocument,
            }
        )

        if api_key is None:
            raise RuntimeError("Mistral API key not specified")

        self.mistral = Mistral(api_key=api_key)

        # Used with Mistral doc upload
        self.unique_id = str(uuid.uuid4())

        print("PDF inited")

    def ocr(self, blob):

        print("Parse PDF...", flush=True)

        pdfbuf = BytesIO(blob)
        pdf = PdfReader(pdfbuf)

        for chunk in chunks(pdf.pages, pages_per_chunk):
            
            print("Get next pages...", flush=True)

            part = PdfWriter()
            for page in chunk:
                part.add_page(page)

            buf = BytesIO()
            part.write_stream(buf)

            print("Upload chunk...", flush=True)

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

            print("OCR...", flush=True)

            processed = self.mistral.ocr.process(
                model="mistral-ocr-latest",
                include_image_base64=True,
                document={
                    "type": "document_url",
                    "document_url": signed_url.url,
                }
            )

            print("Extract markdown...", flush=True)

            markdown = get_combined_markdown(processed)

            print("OCR complete.", flush=True)

            return markdown

    async def handle(self, msg):

        print("PDF message received")

        v = msg.value()

        print(f"Decoding {v.metadata.id}...", flush=True)

        markdown = self.ocr(base64.b64decode(v.data))

        r = TextDocument(
            metadata=v.metadata,
            text=markdown.encode("utf-8"),
        )

        await self.send(r)

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-k', '--api-key',
            default=default_api_key,
            help=f'Mistral API Key'
        )

def run():

    Processor.launch(module, __doc__)

