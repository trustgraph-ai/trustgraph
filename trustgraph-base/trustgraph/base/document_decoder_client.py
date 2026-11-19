
from dataclasses import dataclass

from . request_response_spec import RequestResponseSpec
from .. schema import DocumentDecoderRequest, DocumentDecoderResponse


@dataclass
class DecodedSection:
    document_id: str = ""
    page: int = 0
    section_type: str = "text"


class DocumentDecoderClient:
    async def decode(self, document_id, mode="page", timeout=600):

        sections = []

        async def recipient(resp):
            if resp.error:
                raise RuntimeError(resp.error.message)
            if resp.document_id:
                sections.append(DecodedSection(
                    document_id=resp.document_id,
                    page=resp.page,
                    section_type=resp.section_type,
                ))
            return resp.end_of_stream

        await self.request(
            DocumentDecoderRequest(
                document_id=document_id,
                mode=mode,
            ),
            timeout=timeout,
            recipient=recipient,
        )

        return sections


class DocumentDecoderClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(DocumentDecoderClientSpec, self).__init__(
            request_name=request_name,
            request_schema=DocumentDecoderRequest,
            response_name=response_name,
            response_schema=DocumentDecoderResponse,
            impl=DocumentDecoderClient,
        )
