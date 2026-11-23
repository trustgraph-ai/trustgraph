
from . request_response_spec import RequestResponseSpec
from .. schema import DocumentRagQuery, DocumentRagResponse


class DocumentRagClient:
    async def rag(self, query, collection="default",
                  doc_limit=0, fetch_limit=0,
                  timeout=600):

        accumulated_response = []

        async def recipient(resp):
            if resp.error:
                raise RuntimeError(resp.error.message)

            if resp.message_type == 'chunk':
                if resp.response:
                    accumulated_response.append(resp.response)

            if resp.end_of_session:
                return True

            return False

        await self.request(
            DocumentRagQuery(
                query=query,
                collection=collection,
                doc_limit=doc_limit,
                fetch_limit=fetch_limit,
            ),
            timeout=timeout,
            recipient=recipient,
        )

        return "".join(accumulated_response)


class DocumentRagClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name, optional=False,
    ):
        super(DocumentRagClientSpec, self).__init__(
            request_name=request_name,
            request_schema=DocumentRagQuery,
            response_name=response_name,
            response_schema=DocumentRagResponse,
            impl=DocumentRagClient,
            optional=optional,
        )
