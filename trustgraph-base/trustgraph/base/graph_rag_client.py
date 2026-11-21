
from . request_response_spec import RequestResponseSpec
from .. schema import GraphRagQuery, GraphRagResponse

class GraphRagClient:
    async def rag(self, query, collection="default",
                  entity_limit=0, triple_limit=0,
                  max_subgraph_size=0, max_path_length=0,
                  edge_score_limit=0, edge_limit=0,
                  max_reranker_input=0,
                  chunk_callback=None, explain_callback=None,
                  parent_uri="",
                  grounding_seeds=None,
                  graph_seeds=None,
                  languages=None,
                  traversal_instructions=None,
                  graph=None,
                  timeout=600):
        """
        Execute a graph RAG query with optional streaming callbacks.

        Args:
            query: The question to ask
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
                collection = collection,
                entity_limit = entity_limit,
                triple_limit = triple_limit,
                max_subgraph_size = max_subgraph_size,
                max_path_length = max_path_length,
                edge_score_limit = edge_score_limit,
                edge_limit = edge_limit,
                max_reranker_input = max_reranker_input,
                parent_uri = parent_uri,
                grounding_seeds = grounding_seeds or [],
                graph_seeds = graph_seeds or [],
                languages = languages or [],
                traversal_instructions = traversal_instructions or [],
                graph = graph,
            ),
            timeout=timeout,
            recipient=recipient,
        )

        return "".join(accumulated_response)

class GraphRagClientSpec(RequestResponseSpec):
    def __init__(
            self, request_name, response_name, optional=False,
    ):
        super(GraphRagClientSpec, self).__init__(
            request_name = request_name,
            request_schema = GraphRagQuery,
            response_name = response_name,
            response_schema = GraphRagResponse,
            impl = GraphRagClient,
            optional = optional,
        )

