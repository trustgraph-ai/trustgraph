
from . request_response_spec import RequestResponse, RequestResponseSpec
from .. schema import GraphRagQuery, GraphRagResponse

class GraphRagClient(RequestResponse):
    async def rag(self, query, user="trustgraph", collection="default",
                  chunk_callback=None, explain_callback=None,
                  parent_uri="",
                  timeout=600):
        """
        Execute a graph RAG query with optional streaming callbacks.

        Args:
            query: The question to ask
            user: User identifier
            collection: Collection identifier
            chunk_callback: Optional async callback(text, end_of_stream) for text chunks
            explain_callback: Optional async callback(explain_id, explain_graph, explain_triples) for explain notifications
            timeout: Request timeout in seconds

        Returns:
            Complete response text (accumulated from all chunks)
        """
        accumulated_response = []

        async def recipient(resp):
            if resp.error:
                raise RuntimeError(resp.error.message)

            # Handle explain notifications
            if resp.message_type == 'explain':
                if explain_callback and resp.explain_id:
                    await explain_callback(resp.explain_id, resp.explain_graph, resp.explain_triples)
                return False  # Continue receiving

            # Handle text chunks
            if resp.message_type == 'chunk':
                if resp.response:
                    accumulated_response.append(resp.response)
                if chunk_callback:
                    await chunk_callback(resp.response, resp.end_of_stream)

            # Complete when session ends
            if resp.end_of_session:
                return True

            return False  # Continue receiving

        await self.request(
            GraphRagQuery(
                query = query,
                user = user,
                collection = collection,
                parent_uri = parent_uri,
            ),
            timeout=timeout,
            recipient=recipient,
        )

        return "".join(accumulated_response)

class GraphRagClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name,
    ):
        super(GraphRagClientSpec, self).__init__(
            request_name = request_name,
            request_schema = GraphRagQuery,
            response_name = response_name,
            response_schema = GraphRagResponse,
            impl = GraphRagClient,
        )

