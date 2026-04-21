
import asyncio
import uuid
import logging
from . librarian import LibrarianRequestor

# Module logger
logger = logging.getLogger(__name__)

class DocumentStreamExport:

    def __init__(self, backend):
        self.backend = backend

    async def process(self, data, error, ok, request):

        workspace = request.query.get("workspace", "default")
        document_id = request.query.get("document-id")
        chunk_size = int(request.query.get("chunk-size", 1024 * 1024))

        if not document_id:
            return await error("Missing required parameter: document-id")

        response = await ok()

        lr = LibrarianRequestor(
            backend=self.backend,
            consumer="api-gateway-doc-stream-" + str(uuid.uuid4()),
            subscriber="api-gateway-doc-stream-" + str(uuid.uuid4()),
        )

        try:

            await lr.start()

            async def responder(resp, fin):
                if "content" in resp:
                    content = resp["content"]
                    # Content is base64 encoded, write as-is for client to decode
                    # Or decode here and write raw bytes
                    import base64
                    chunk_data = base64.b64decode(content)
                    await response.write(chunk_data)

            await lr.process(
                {
                    "operation": "stream-document",
                    "workspace": workspace,
                    "document-id": document_id,
                    "chunk-size": chunk_size,
                },
                responder
            )

        except Exception as e:

            logger.error(f"Document stream exception: {e}", exc_info=True)

        finally:

            await lr.stop()

        await response.write_eof()

        return response
