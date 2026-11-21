
from dataclasses import dataclass

from . request_response_spec import RequestResponseSpec
from .. schema import ChunkerRequest, ChunkerResponse


@dataclass
class ChunkReference:
    document_id: str = ""
    index: int = 0
    char_offset: int = 0
    char_length: int = 0


class ChunkerClient:
    async def chunk(self, document_id, chunk_size=0, chunk_overlap=0,
                    timeout=300):

        chunks = []

        async def recipient(resp):
            if resp.error:
                raise RuntimeError(resp.error.message)
            if resp.document_id:
                chunks.append(ChunkReference(
                    document_id=resp.document_id,
                    index=resp.index,
                    char_offset=resp.char_offset,
                    char_length=resp.char_length,
                ))
            return resp.end_of_stream

        await self.request(
            ChunkerRequest(
                document_id=document_id,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            ),
            timeout=timeout,
            recipient=recipient,
        )

        return chunks


class ChunkerClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name, optional=False,
    ):
        super(ChunkerClientSpec, self).__init__(
            request_name=request_name,
            request_schema=ChunkerRequest,
            response_name=response_name,
            response_schema=ChunkerResponse,
            impl=ChunkerClient,
            optional=optional,
        )
