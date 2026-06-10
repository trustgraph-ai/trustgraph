from contextlib import asynccontextmanager
from typing import Optional
import os
import time
from typing import AsyncGenerator, Any, Dict, List
import asyncio
import logging
import json
import uuid
import argparse
from dataclasses import dataclass, field
from collections.abc import AsyncIterator
from functools import partial

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.middleware.auth_context import get_access_token

from trustgraph.base.logging import add_logging_args, setup_logging

from . tg_socket import WebSocketManager, _token_key

logger = logging.getLogger(__name__)


# Wire-format Term type codes (match TermTranslator compact keys)
_TERM_TYPES = {
    "iri": "i",
    "literal": "l",
    "blank": "b",
}


def _make_term(value: str, term_type: str) -> dict:
    """Build a compact-key Term dict for the gateway wire format.

    Args:
        value: The term value (IRI string, literal text, or blank node id).
        term_type: One of "iri", "literal", "blank".
    """
    t = _TERM_TYPES.get(term_type)
    if t is None:
        raise ValueError(
            f"Unknown term type '{term_type}' — "
            f"expected one of: {', '.join(_TERM_TYPES)}"
        )

    if t == "i":
        return {"t": t, "i": value}
    elif t == "l":
        return {"t": t, "v": value}
    elif t == "b":
        return {"t": t, "d": value}
    return {"t": t}

# ── Security boundary: MCP client → MCP server ──
# The MCP client authenticates to this server via a Bearer token in the
# HTTP Authorization header.  The SDK's auth middleware extracts and
# verifies the token before any tool handler runs.
#
# We implement a pass-through TokenVerifier: the gateway is the real
# authority, so we accept any non-empty Bearer token here and forward
# it to the gateway for validation.  The gateway's in-band auth
# protocol and IAM regime decide whether the token is valid.
#
# This means an invalid token will connect to the MCP server but will
# fail when the first WebSocket auth frame is sent to the gateway.
# That is intentional — the gateway is the single source of truth.


class PassthroughTokenVerifier(TokenVerifier):
    """Accept any non-empty Bearer token and forward it downstream.

    The TrustGraph gateway is the authority for token validation, not
    this MCP server.  We store the raw token in the AccessToken so that
    tool handlers can retrieve it via ``get_access_token().token`` and
    forward it to the gateway.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token:
            return None
        return AccessToken(
            token=token,
            client_id="mcp-caller",
            scopes=[],
        )


@dataclass
class AppContext:
    sockets: dict[str, WebSocketManager] = field(default_factory=dict)
    websocket_url: str = ""


@asynccontextmanager
async def app_lifespan(
    server: FastMCP,
    websocket_url: str = "ws://api-gateway:8088/api/v1/socket",
) -> AsyncIterator[AppContext]:
    """Manage per-server state: the pool of per-caller WebSocket
    connections to the gateway."""

    sockets: dict[str, WebSocketManager] = {}

    try:
        yield AppContext(sockets=sockets, websocket_url=websocket_url)
    finally:

        logger.info("Shutting down — closing %d WebSocket(s)", len(sockets))

        for key, manager in sockets.items():
            try:
                await manager.stop()
            except Exception as e:
                logger.warning("Error closing socket %s: %s", key, e)

        logger.info("Shutdown complete")


def _require_token() -> str:
    """Extract the caller's Bearer token from the MCP auth context.

    Raises RuntimeError if no token is present (the caller did not
    authenticate).
    """
    # ── Security boundary: token extraction ──
    # get_access_token() reads the contextvar set by the SDK's
    # AuthContextMiddleware.  The token was placed there by
    # PassthroughTokenVerifier.verify_token() and is the raw Bearer
    # value from the MCP client's Authorization header.
    access = get_access_token()
    if access is None or not access.token:
        raise RuntimeError(
            "Authentication required — send a Bearer token in the "
            "Authorization header"
        )
    return access.token


async def get_socket_manager(ctx, token):
    """Return (or create) an authenticated WebSocket for this token.

    Each unique token gets its own WebSocket connection so that
    gateway-side identity, workspace binding, and capability scoping
    are preserved per caller.
    """

    lifespan_context = ctx.request_context.lifespan_context
    sockets = lifespan_context.sockets
    websocket_url = lifespan_context.websocket_url

    key = _token_key(token)

    if key in sockets:
        manager = sockets[key]
        if manager.socket is not None:
            return manager
        # Socket was closed (e.g. server-side timeout) — reconnect.
        del sockets[key]

    logger.info("Opening authenticated WebSocket to %s …", websocket_url)

    manager = WebSocketManager(websocket_url, token=token)
    await manager.start()

    # Verify the token is valid by calling whoami.  This confirms the
    # gateway accepted the token and gives us the caller's identity.
    try:
        identity = await manager.whoami()
        logger.info(
            "WebSocket ready — caller: %s",
            identity.get("handle", "unknown"),
        )
    except Exception as e:
        await manager.stop()
        raise RuntimeError(
            f"Token rejected by gateway (whoami failed): {e}"
        ) from e

    sockets[key] = manager
    return manager


@dataclass
class EmbeddingsResponse:
    vectors: List[List[float]]

@dataclass
class TextCompletionResponse:
    response: str

@dataclass
class GraphRagResponse:
    response: str

@dataclass
class AgentResponse:
    answer: str

@dataclass
class Value:
    v: str
    e: bool

@dataclass
class GraphEmbeddingsQueryResponse:
    entities: List[Dict[str, Any]]

@dataclass
class ConfigResponse:
    config: Dict[str, Any]

@dataclass
class ConfigGetResponse:
    values: List[Dict[str, Any]]

@dataclass
class ConfigTokenCostsResponse:
    costs: List[Dict[str, Any]]

@dataclass
class KnowledgeCoresResponse:
    ids: List[str]

@dataclass
class FlowsResponse:
    flow_ids: List[str]

@dataclass
class FlowResponse:
    flow: Dict[str, Any]

@dataclass
class FlowClassesResponse:
    class_names: List[str]

@dataclass
class FlowClassResponse:
    class_definition: Dict[str, Any]

@dataclass
class DocumentsResponse:
    document_metadatas: List[Dict[str, Any]]

@dataclass
class ProcessingResponse:
    processing_metadatas: List[Dict[str, Any]]

@dataclass
class DeleteKgCoreResponse:
    pass

@dataclass
class LoadKgCoreResponse:
    pass

@dataclass
class GetKgCoreResponse:
    chunks: List[Dict[str, Any]]

@dataclass
class StartFlowResponse:
    pass

@dataclass
class StopFlowResponse:
    pass

@dataclass
class LoadDocumentResponse:
    pass

@dataclass
class RemoveDocumentResponse:
    pass

@dataclass
class AddProcessingResponse:
    pass

@dataclass
class TriplesQueryResponse:
    triples: List[Dict[str, Any]]

@dataclass
class PutConfigResponse:
    pass

@dataclass
class DeleteConfigResponse:
    pass

@dataclass
class SparqlQueryResponse:
    query_type: str
    variables: List[str]
    bindings: List[Dict[str, Any]]
    ask_result: bool
    triples: List[Dict[str, Any]]

@dataclass
class GraphQLQueryResponse:
    data: Any
    errors: List[Dict[str, Any]]

@dataclass
class GetPromptsResponse:
    prompts: List[str]

@dataclass
class GetPromptResponse:
    prompt: Dict[str, Any]

@dataclass
class GetSystemPromptResponse:
    prompt: str


class McpServer:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        websocket_url: str = "ws://api-gateway:8088/api/v1/socket",
        auth_issuer: str = "",
        auth_resource_url: str = "",
    ):
        self.host = host
        self.port = port
        self.websocket_url = websocket_url

        lifespan_with_url = partial(
            app_lifespan, websocket_url=websocket_url,
        )

        # ── Security: MCP-level auth configuration ──
        # The SDK requires AuthSettings whenever a token_verifier is
        # present.  The issuer_url tells MCP clients where to obtain
        # tokens; resource_server_url identifies this server in OAuth
        # protected-resource metadata.
        #
        # The PassthroughTokenVerifier accepts any non-empty Bearer
        # token — real validation happens at the gateway.  This is
        # intentional: the gateway is the single source of truth for
        # identity and capability checks.
        from mcp.server.auth.settings import AuthSettings

        auth_settings = AuthSettings(
            issuer_url=auth_issuer or f"http://{host}:{port}",
            resource_server_url=auth_resource_url or f"http://{host}:{port}",
        )

        self.mcp = FastMCP(
            "TrustGraph",
            dependencies=["trustgraph-base"],
            host=self.host,
            port=self.port,
            lifespan=lifespan_with_url,
            token_verifier=PassthroughTokenVerifier(),
            auth=auth_settings,
        )
        self._register_tools()

    def _register_tools(self):
        """Register all MCP tools"""
        self.mcp.tool()(self.embeddings)
        self.mcp.tool()(self.text_completion)
        self.mcp.tool()(self.graph_rag)
        self.mcp.tool()(self.agent)
        self.mcp.tool()(self.triples_query)
        self.mcp.tool()(self.sparql_query)
        self.mcp.tool()(self.graphql_query)
        self.mcp.tool()(self.graph_embeddings_query)
        self.mcp.tool()(self.get_config_all)
        self.mcp.tool()(self.get_config)
        self.mcp.tool()(self.put_config)
        self.mcp.tool()(self.delete_config)
        self.mcp.tool()(self.get_prompts)
        self.mcp.tool()(self.get_prompt)
        self.mcp.tool()(self.get_system_prompt)
        self.mcp.tool()(self.get_token_costs)
        self.mcp.tool()(self.get_knowledge_cores)
        self.mcp.tool()(self.delete_kg_core)
        self.mcp.tool()(self.load_kg_core)
        self.mcp.tool()(self.get_kg_core)
        self.mcp.tool()(self.get_flows)
        self.mcp.tool()(self.get_flow)
        self.mcp.tool()(self.get_flow_classes)
        self.mcp.tool()(self.get_flow_class)
        self.mcp.tool()(self.start_flow)
        self.mcp.tool()(self.stop_flow)
        self.mcp.tool()(self.get_documents)
        self.mcp.tool()(self.get_processing)
        self.mcp.tool()(self.load_document)
        self.mcp.tool()(self.remove_document)
        self.mcp.tool()(self.add_processing)

    def run(self):
        """Run the MCP server"""
        self.mcp.run(transport="streamable-http")

    async def _get_manager(self, ctx):
        """Get an authenticated WebSocket manager for the current caller.

        Extracts the Bearer token from the MCP auth context and returns
        a per-token WebSocket connection to the gateway.
        """
        token = _require_token()
        return await get_socket_manager(ctx, token)

    async def embeddings(
            self,
            texts: List[str],
            flow_id: str | None = None,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> EmbeddingsResponse:
        """
        Generate vector embeddings for the given texts using TrustGraph's embedding models.

        This tool converts text into high-dimensional vectors that capture semantic meaning,
        enabling similarity searches, clustering, and other vector-based operations.

        Args:
            texts: List of input texts to convert into embeddings. Each text can be a
                   sentence, paragraph, or document.
            flow_id: Optional flow identifier to use for processing (default: "default").
                     Different flows may use different embedding models or configurations.
            workspace: Optional workspace to query. If omitted, uses the caller's
                       default workspace.

        Returns:
            EmbeddingsResponse containing a list of vectors, one per input text.
        """

        logger.info("Embeddings request")

        if flow_id is None: flow_id = "default"

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Computing embeddings via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {"texts": texts}

        gen = manager.request(
            "embeddings", request_data, flow_id, workspace=workspace,
        )

        async for response in gen:
            vectors = response.get("vectors", [[]])
            break

        return EmbeddingsResponse(vectors=vectors)

    async def text_completion(
            self,
            prompt: str,
            system: str | None = None,
            flow_id: str | None = None,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> TextCompletionResponse:
        """
        Generate text completions using TrustGraph's language models.

        Args:
            prompt: The main prompt or question to send to the language model.
            system: Optional system prompt that sets the context, role, or behavior
                    for the AI assistant.
            flow_id: Optional flow identifier (default: "default").
            workspace: Optional workspace to query. If omitted, uses the caller's
                       default workspace.

        Returns:
            TextCompletionResponse containing the generated text response from the model.
        """

        if system is None: system = ""
        if flow_id is None: flow_id = "default"

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Generating text completion via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {"system": system, "prompt": prompt}

        gen = manager.request(
            "text-completion", request_data, flow_id, workspace=workspace,
        )

        async for response in gen:
            text = response.get("response", "")
            break

        return TextCompletionResponse(response=text)

    async def graph_rag(
            self,
            question: str,
            collection: str | None = None,
            entity_limit: int | None = None,
            triple_limit: int | None = None,
            max_subgraph_size: int | None = None,
            max_path_length: int | None = None,
            flow_id: str | None = None,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> GraphRagResponse:
        """
        Perform Graph-based Retrieval Augmented Generation (GraphRAG) queries.

        GraphRAG combines knowledge graph traversal with language model generation to provide
        contextually rich answers.

        Args:
            question: The question or query to answer using the knowledge graph.
            collection: Knowledge collection to query (default: "default").
            entity_limit: Maximum number of entities to retrieve during graph traversal.
            triple_limit: Maximum number of relationship triples to consider.
            max_subgraph_size: Maximum size of the subgraph to extract for context.
            max_path_length: Maximum path length to traverse in the knowledge graph.
            flow_id: Processing flow to use (default: "default").
            workspace: Optional workspace to query. If omitted, uses the caller's
                       default workspace.

        Returns:
            GraphRagResponse containing the generated answer informed by knowledge graph context.
        """

        if collection is None: collection = "default"
        if flow_id is None: flow_id = "default"

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Processing GraphRAG query via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "query": question
        }

        if collection: request_data["collection"] = collection
        if entity_limit: request_data["entity_limit"] = entity_limit
        if triple_limit: request_data["triple_limit"] = triple_limit
        if max_subgraph_size: request_data["max_subgraph_size"] = max_subgraph_size
        if max_path_length: request_data["max_path_length"] = max_path_length

        gen = manager.request(
            "graph-rag", request_data, flow_id, workspace=workspace,
        )

        text_chunks = []
        async for response in gen:
            message_type = response.get("message_type", "chunk")

            if message_type == "chunk":
                chunk_text = response.get("response", "")
                if chunk_text:
                    text_chunks.append(chunk_text)

            if response.get("end_of_session"):
                break

        return GraphRagResponse(response="".join(text_chunks))

    async def agent(
            self,
            question: str,
            collection: str | None = None,
            flow_id: str | None = None,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> AgentResponse:
        """
        Execute intelligent agent queries with reasoning and tool usage capabilities.

        Args:
            question: The question or task for the agent to solve.
            collection: Knowledge collection the agent can access (default: "default").
            flow_id: Agent workflow to use (default: "default").
            workspace: Optional workspace to query. If omitted, uses the caller's
                       default workspace.

        Returns:
            AgentResponse containing the final answer after the agent's reasoning process.
        """

        if collection is None: collection = "default"
        if flow_id is None: flow_id = "default"

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Processing agent query via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "question": question
        }

        if collection: request_data["collection"] = collection

        gen = manager.request(
            "agent", request_data, flow_id, workspace=workspace,
        )

        async for response in gen:

            logger.debug("Agent response: %s", response)

            if ctx:
                if "thought" in response:
                    await ctx.session.send_log_message(
                        level="info",
                        data=f"Thinking: {response['thought']}",
                        logger="notification_stream",
                        related_request_id=ctx.request_id,
                    )

                if "observation" in response:
                    await ctx.session.send_log_message(
                        level="info",
                        data=f"Observation: {response['observation']}",
                        logger="notification_stream",
                        related_request_id=ctx.request_id,
                    )

            if "answer" in response:
                answer = response.get("answer", "")
                return AgentResponse(answer=answer)

    async def triples_query(
            self,
            s: str | None = None,
            s_type: str | None = None,
            p: str | None = None,
            p_type: str | None = None,
            o: str | None = None,
            o_type: str | None = None,
            collection: str | None = None,
            graph: str | None = None,
            limit: int | None = None,
            flow_id: str | None = None,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> TriplesQueryResponse:
        """
        Query knowledge graph triples using subject-predicate-object patterns.

        Each of s, p, o is an RDF term value. Use the corresponding _type
        parameter to specify the term kind:
          - "iri" (default for s and p): an IRI / entity reference
          - "literal" (default for o): a plain literal value
          - "blank": a blank node identifier

        Args:
            s: Subject value to match. Leave None for wildcard.
            s_type: Subject term type: "iri" (default), "literal", or "blank".
            p: Predicate value to match. Leave None for wildcard.
            p_type: Predicate term type: "iri" (default), "literal", or "blank".
            o: Object value to match. Leave None for wildcard.
            o_type: Object term type: "iri", "literal" (default), or "blank".
            collection: Knowledge collection to query (default: "default").
            graph: Named graph IRI to restrict the query. None = default graph,
                   "*" = all graphs.
            limit: Maximum number of triples to return (default: 20).
            flow_id: Processing flow identifier (default: "default").
            workspace: Optional workspace to query. If omitted, uses the caller's
                       default workspace.

        Returns:
            TriplesQueryResponse containing matching triples from the knowledge graph.
        """

        if flow_id is None: flow_id = "default"
        if limit is None: limit = 20
        if collection is None: collection = "default"

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Processing triples query via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "limit": limit,
            "collection": collection,
        }

        if s is not None:
            request_data["s"] = _make_term(s, s_type or "iri")

        if p is not None:
            request_data["p"] = _make_term(p, p_type or "iri")

        if o is not None:
            request_data["o"] = _make_term(o, o_type or "literal")

        if graph is not None:
            request_data["g"] = graph

        gen = manager.request(
            "triples", request_data, flow_id, workspace=workspace,
        )

        async for response in gen:
            triples = response.get("response", [])
            break

        return TriplesQueryResponse(triples=triples)

    async def sparql_query(
            self,
            query: str,
            collection: str | None = None,
            limit: int | None = None,
            flow_id: str | None = None,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> SparqlQueryResponse:
        """
        Execute a SPARQL query against the knowledge graph.

        Supports SELECT, ASK, CONSTRUCT, and DESCRIBE query forms.

        Args:
            query: SPARQL query string (e.g. "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10").
            collection: Knowledge collection to query (default: "default").
            limit: Safety limit on number of results (default: 10000).
            flow_id: Processing flow identifier (default: "default").
            workspace: Optional workspace to query. If omitted, uses the caller's
                       default workspace.

        Returns:
            SparqlQueryResponse containing the query results. The structure depends
            on query type:
              - SELECT: variables (column names) and bindings (rows of Term values)
              - ASK: ask_result (boolean)
              - CONSTRUCT/DESCRIBE: triples
        """

        if collection is None: collection = "default"
        if flow_id is None: flow_id = "default"
        if limit is None: limit = 10000

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Processing SPARQL query via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "query": query,
            "collection": collection,
            "limit": limit,
        }

        gen = manager.request(
            "sparql", request_data, flow_id, workspace=workspace,
        )

        async for response in gen:
            query_type = response.get("query-type", "")
            return SparqlQueryResponse(
                query_type=query_type,
                variables=response.get("variables", []),
                bindings=response.get("bindings", []),
                ask_result=response.get("ask-result", False),
                triples=response.get("triples", []),
            )

    async def graphql_query(
            self,
            query: str,
            collection: str | None = None,
            variables: Dict[str, Any] | None = None,
            operation_name: str | None = None,
            flow_id: str | None = None,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> GraphQLQueryResponse:
        """
        Execute a GraphQL query against structured data (rows).

        Queries structured data schemas that have been loaded into TrustGraph.
        The available types and fields depend on the schemas configured in the
        target workspace.

        Args:
            query: GraphQL query string (e.g. '{ customers(where: {status: {eq: "active"}}) { id name } }').
            collection: Data collection to query (default: "default").
            variables: Optional GraphQL variables as a dict.
            operation_name: Optional operation name for multi-operation documents.
            flow_id: Processing flow identifier (default: "default").
            workspace: Optional workspace to query. If omitted, uses the caller's
                       default workspace.

        Returns:
            GraphQLQueryResponse containing data (the query result) and errors
            (any GraphQL field-level errors).
        """

        if collection is None: collection = "default"
        if flow_id is None: flow_id = "default"

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Processing GraphQL query via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "query": query,
            "collection": collection,
            "variables": variables or {},
        }

        if operation_name is not None:
            request_data["operation_name"] = operation_name

        gen = manager.request(
            "rows", request_data, flow_id, workspace=workspace,
        )

        async for response in gen:
            return GraphQLQueryResponse(
                data=response.get("data"),
                errors=response.get("errors", []),
            )

    async def graph_embeddings_query(
            self,
            vectors: List[List[float]],
            limit: int | None = None,
            flow_id: str | None = None,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> GraphEmbeddingsQueryResponse:
        """
        Find entities in the knowledge graph using vector similarity search.

        Args:
            vectors: List of embedding vectors to search with.
            limit: Maximum number of similar entities to return (default: 20).
            flow_id: Processing flow identifier (default: "default").
            workspace: Optional workspace to query. If omitted, uses the caller's
                       default workspace.

        Returns:
            GraphEmbeddingsQueryResponse containing entities ranked by similarity.
        """

        if flow_id is None: flow_id = "default"
        if limit is None: limit = 20

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Processing graph embeddings query via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "vectors": vectors,
            "limit": limit
        }

        gen = manager.request(
            "graph-embeddings", request_data, flow_id, workspace=workspace,
        )

        async for response in gen:
            entities = response.get("entities", [])
            break

        return GraphEmbeddingsQueryResponse(entities=entities)

    async def get_config_all(
            self,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> ConfigResponse:
        """
        Retrieve the complete TrustGraph system configuration.

        Args:
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            ConfigResponse containing the full configuration as a nested dictionary.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Retrieving all configuration via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "config"
        }

        gen = manager.request("config", request_data, None, workspace=workspace)

        async for response in gen:
            config = response.get("config", {})
            break

        return ConfigResponse(config=config)

    async def get_config(
            self,
            keys: List[Dict[str, str]],
            workspace: str | None = None,
            ctx: Context = None,
    ) -> ConfigGetResponse:
        """
        Retrieve specific configuration values by key.

        Args:
            keys: List of configuration keys to retrieve. Each key should be a dict with
                  'type' and 'key' fields.
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            ConfigGetResponse containing the requested configuration values.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Retrieving specific configuration via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "get",
            "keys": keys
        }

        gen = manager.request("config", request_data, None, workspace=workspace)

        async for response in gen:
            values = response.get("values", [])
            break

        return ConfigGetResponse(values=values)

    async def put_config(
            self,
            values: List[Dict[str, str]],
            workspace: str | None = None,
            ctx: Context = None,
    ) -> PutConfigResponse:
        """
        Update system configuration values.

        Args:
            values: List of configuration updates. Each should be a dict with
                    'type', 'key', and 'value' fields.
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            PutConfigResponse confirming the configuration update.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Updating configuration via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "put",
            "values": values
        }

        gen = manager.request("config", request_data, None, workspace=workspace)

        async for response in gen:
            return PutConfigResponse()

    async def delete_config(
            self,
            keys: List[Dict[str, str]],
            workspace: str | None = None,
            ctx: Context = None,
    ) -> DeleteConfigResponse:
        """
        Delete specific configuration entries from the system.

        Args:
            keys: List of configuration keys to delete. Each should be a dict with
                  'type' and 'key' fields.
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            DeleteConfigResponse confirming the deletion.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Deleting configuration via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "delete",
            "keys": keys
        }

        gen = manager.request("config", request_data, None, workspace=workspace)

        async for response in gen:
            return DeleteConfigResponse()

    async def get_prompts(
            self,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> GetPromptsResponse:
        """
        List all available prompt templates in the system.

        Args:
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            GetPromptsResponse containing a list of available prompt template IDs.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Retrieving prompt templates via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "config"
        }

        gen = manager.request("config", request_data, None, workspace=workspace)

        async for response in gen:
            config = response.get("config", {})
            prompt_config = config.get("prompt", {})
            template_index = prompt_config.get("template-index", "[]")
            prompts = json.loads(template_index) if isinstance(template_index, str) else template_index
            return GetPromptsResponse(prompts=prompts)

    async def get_prompt(
            self,
            prompt_id: str,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> GetPromptResponse:
        """
        Retrieve a specific prompt template by ID.

        Args:
            prompt_id: The unique identifier of the prompt template to retrieve.
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            GetPromptResponse containing the complete prompt template.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data=f"Retrieving prompt template '{prompt_id}' via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "config"
        }

        gen = manager.request("config", request_data, None, workspace=workspace)

        async for response in gen:
            config = response.get("config", {})
            prompt_config = config.get("prompt", {})
            template_key = f"template.{prompt_id}"
            template_data = prompt_config.get(template_key, "{}")
            prompt = json.loads(template_data) if isinstance(template_data, str) else template_data
            return GetPromptResponse(prompt=prompt)

    async def get_system_prompt(
            self,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> GetSystemPromptResponse:
        """
        Retrieve the current system prompt configuration.

        Args:
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            GetSystemPromptResponse containing the system prompt text.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Retrieving system prompt via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "config"
        }

        gen = manager.request("config", request_data, None, workspace=workspace)

        async for response in gen:
            config = response.get("config", {})
            prompt_config = config.get("prompt", {})
            system_data = prompt_config.get("system", "{}")
            system_prompt = json.loads(system_data) if isinstance(system_data, str) else system_data
            return GetSystemPromptResponse(prompt=system_prompt)

    async def get_token_costs(
            self,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> ConfigTokenCostsResponse:
        """
        Retrieve token pricing information for all configured AI models.

        Args:
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            ConfigTokenCostsResponse containing pricing data for each model.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Retrieving token costs via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "getvalues",
            "type": "token-costs"
        }

        gen = manager.request("config", request_data, None, workspace=workspace)

        async for response in gen:
            values = response.get("values", [])
            costs = []
            for item in values:
                try:
                    value_data = json.loads(item.get("value", "{}")) if isinstance(item.get("value"), str) else item.get("value", {})
                    costs.append({
                        "model": item.get("key"),
                        "input_price": value_data.get("input_price"),
                        "output_price": value_data.get("output_price")
                    })
                except (json.JSONDecodeError, AttributeError):
                    continue
            break

        return ConfigTokenCostsResponse(costs=costs)

    async def get_knowledge_cores(
            self,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> KnowledgeCoresResponse:
        """
        List all available knowledge graph cores in the current workspace.

        Args:
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            KnowledgeCoresResponse containing a list of available knowledge core IDs.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Retrieving knowledge graph cores via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "list-kg-cores",
        }

        gen = manager.request(
            "knowledge", request_data, None, workspace=workspace,
        )

        async for response in gen:
            ids = response.get("ids", [])
            break

        return KnowledgeCoresResponse(ids=ids)

    async def delete_kg_core(
            self,
            core_id: str,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> DeleteKgCoreResponse:
        """
        Permanently delete a knowledge graph core.

        Args:
            core_id: Unique identifier of the knowledge core to delete.
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            DeleteKgCoreResponse confirming the deletion.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data=f"Deleting knowledge graph core '{core_id}' via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "delete-kg-core",
            "id": core_id,
        }

        gen = manager.request(
            "knowledge", request_data, None, workspace=workspace,
        )

        async for response in gen:
            break

        return DeleteKgCoreResponse()

    async def load_kg_core(
            self,
            core_id: str,
            flow: str,
            collection: str | None = None,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> LoadKgCoreResponse:
        """
        Load a knowledge graph core into the active system for querying.

        Args:
            core_id: Unique identifier of the knowledge core to load.
            flow: Processing flow to use for loading the core.
            collection: Target collection name (default: "default").
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            LoadKgCoreResponse confirming the core has been loaded.
        """

        if collection is None: collection = "default"

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data=f"Loading knowledge graph core '{core_id}' via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "load-kg-core",
            "id": core_id,
            "flow": flow,
            "collection": collection
        }

        gen = manager.request(
            "knowledge", request_data, None, workspace=workspace,
        )

        async for response in gen:
            break

        return LoadKgCoreResponse()

    async def get_kg_core(
            self,
            core_id: str,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> GetKgCoreResponse:
        """
        Download and retrieve the complete content of a knowledge graph core.

        Args:
            core_id: Unique identifier of the knowledge core to retrieve.
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            GetKgCoreResponse containing all chunks of the knowledge core data.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data=f"Retrieving knowledge graph core '{core_id}' via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "get-kg-core",
            "id": core_id,
        }

        chunks = []
        gen = manager.request(
            "knowledge", request_data, None, workspace=workspace,
        )

        async for response in gen:
            if response.get("eos", False):
                if ctx:
                    await ctx.session.send_log_message(
                        level="info",
                        data="Completed streaming KG core data",
                        logger="notification_stream",
                        related_request_id=ctx.request_id,
                    )
                break
            else:
                chunks.append(response)
                if ctx:
                    await ctx.session.send_log_message(
                        level="info",
                        data=f"Received KG core chunk ({len(chunks)} chunks so far)",
                        logger="notification_stream",
                        related_request_id=ctx.request_id,
                    )

        return GetKgCoreResponse(chunks=chunks)

    async def get_flows(
            self,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> FlowsResponse:
        """
        List all available processing flows in the system.

        Args:
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            FlowsResponse containing a list of available flow identifiers.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Retrieving available flows via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "list-flows"
        }

        gen = manager.request(
            "flow", request_data, None, workspace=workspace,
        )

        async for response in gen:
            flow_ids = response.get("flow-ids", [])
            break

        return FlowsResponse(flow_ids=flow_ids)

    async def get_flow(
            self,
            flow_id: str,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> FlowResponse:
        """
        Retrieve the complete definition of a specific processing flow.

        Args:
            flow_id: Unique identifier of the flow to retrieve.
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            FlowResponse containing the complete flow definition.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data=f"Retrieving flow definition for '{flow_id}' via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "get-flow",
            "flow-id": flow_id,
        }

        gen = manager.request(
            "flow", request_data, None, workspace=workspace,
        )

        async for response in gen:
            flow_data = response.get("flow", "{}")
            flow = json.loads(flow_data) if isinstance(flow_data, str) else flow_data
            break

        return FlowResponse(flow=flow)

    async def get_flow_classes(
            self,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> FlowClassesResponse:
        """
        List all available flow class templates.

        Args:
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            FlowClassesResponse containing a list of available flow class names.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Retrieving flow classes via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "list-classes"
        }

        gen = manager.request(
            "flow", request_data, None, workspace=workspace,
        )

        async for response in gen:
            class_names = response.get("class-names", [])
            break

        return FlowClassesResponse(class_names=class_names)

    async def get_flow_class(
            self,
            class_name: str,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> FlowClassResponse:
        """
        Retrieve the definition of a specific flow class template.

        Args:
            class_name: Name of the flow class to retrieve.
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            FlowClassResponse containing the flow class definition.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data=f"Retrieving flow class definition for '{class_name}' via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "get-class",
            "class-name": class_name
        }

        gen = manager.request(
            "flow", request_data, None, workspace=workspace,
        )

        async for response in gen:
            class_def_data = response.get("class-definition", "{}")
            class_definition = json.loads(class_def_data) if isinstance(class_def_data, str) else class_def_data
            break

        return FlowClassResponse(class_definition=class_definition)

    async def start_flow(
            self,
            flow_id: str,
            class_name: str,
            description: str,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> StartFlowResponse:
        """
        Create and start a new processing flow instance.

        Args:
            flow_id: Unique identifier for the new flow instance.
            class_name: Flow class template to use for creating the flow.
            description: Human-readable description of the flow's purpose.
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            StartFlowResponse confirming the flow has been started.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data=f"Starting flow '{flow_id}' with class '{class_name}' via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "start-flow",
            "flow-id": flow_id,
            "class-name": class_name,
            "description": description
        }

        gen = manager.request(
            "flow", request_data, None, workspace=workspace,
        )

        async for response in gen:
            break

        return StartFlowResponse()

    async def stop_flow(
            self,
            flow_id: str,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> StopFlowResponse:
        """
        Stop a running flow instance.

        Args:
            flow_id: Unique identifier of the flow instance to stop.
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            StopFlowResponse confirming the flow has been stopped.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data=f"Stopping flow '{flow_id}' via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "stop-flow",
            "flow-id": flow_id
        }

        gen = manager.request(
            "flow", request_data, None, workspace=workspace,
        )

        async for response in gen:
            break

        return StopFlowResponse()

    async def get_documents(
            self,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> DocumentsResponse:
        """
        List all documents stored in the TrustGraph document library.

        Args:
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            DocumentsResponse containing metadata for each document.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Retrieving documents list via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "list-documents",
        }

        gen = manager.request(
            "librarian", request_data, None, workspace=workspace,
        )

        async for response in gen:
            document_metadatas = response.get("document-metadatas", [])
            break

        return DocumentsResponse(document_metadatas=document_metadatas)

    async def get_processing(
            self,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> ProcessingResponse:
        """
        List all documents currently in the processing queue.

        Args:
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            ProcessingResponse containing processing metadata.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Retrieving processing list via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "list-processing",
        }

        gen = manager.request(
            "librarian", request_data, None, workspace=workspace,
        )

        async for response in gen:
            processing_metadatas = response.get("processing-metadatas", [])
            break

        return ProcessingResponse(processing_metadatas=processing_metadatas)

    async def load_document(
            self,
            document: str,
            document_id: str | None = None,
            metadata: List[Dict[str, Any]] | None = None,
            mime_type: str = "",
            title: str = "",
            comments: str = "",
            tags: List[str] | None = None,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> LoadDocumentResponse:
        """
        Upload a document to the TrustGraph document library.

        Args:
            document: The document content as a string. For binary files,
                      this should be base64-encoded content.
            document_id: Optional unique identifier. If not provided, one will be generated.
            metadata: Optional list of custom metadata key-value pairs.
            mime_type: MIME type of the document.
            title: Human-readable title for the document.
            comments: Optional description or notes about the document.
            tags: List of tags for categorizing the document.
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            LoadDocumentResponse confirming the document has been stored.
        """

        if tags is None: tags = []

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data="Loading document to library via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        import time
        timestamp = int(time.time())

        request_data = {
            "operation": "add-document",
            "document-metadata": {
                "id": document_id,
                "time": timestamp,
                "kind": mime_type,
                "title": title,
                "comments": comments,
                "metadata": metadata,
                "tags": tags
            },
            "content": document
        }

        gen = manager.request(
            "librarian", request_data, None, workspace=workspace,
        )

        async for response in gen:
            break

        return LoadDocumentResponse()

    async def remove_document(
            self,
            document_id: str,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> RemoveDocumentResponse:
        """
        Permanently remove a document from the library.

        Args:
            document_id: Unique identifier of the document to remove.
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            RemoveDocumentResponse confirming the document has been deleted.
        """

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data=f"Removing document '{document_id}' from library via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        request_data = {
            "operation": "remove-document",
            "document-id": document_id,
        }

        gen = manager.request(
            "librarian", request_data, None, workspace=workspace,
        )

        async for response in gen:
            break

        return RemoveDocumentResponse()

    async def add_processing(
            self,
            processing_id: str,
            document_id: str,
            flow: str,
            collection: str | None = None,
            tags: List[str] | None = None,
            workspace: str | None = None,
            ctx: Context = None,
    ) -> AddProcessingResponse:
        """
        Queue a document for processing through a specific workflow.

        Args:
            processing_id: Unique identifier for this processing job.
            document_id: ID of the document to process (must exist in library).
            flow: Processing flow to use.
            collection: Target collection for processed knowledge (default: "default").
            tags: Optional tags for categorizing this processing job.
            workspace: Optional workspace. If omitted, uses the caller's
                       default workspace.

        Returns:
            AddProcessingResponse confirming the document has been queued.
        """

        if collection is None: collection = "default"
        if tags is None: tags = []

        manager = await self._get_manager(ctx)

        if ctx:
            await ctx.session.send_log_message(
                level="info",
                data=f"Adding document '{document_id}' to processing queue via websocket...",
                logger="notification_stream",
                related_request_id=ctx.request_id,
            )

        import time
        timestamp = int(time.time())

        request_data = {
            "operation": "add-processing",
            "processing-metadata": {
                "id": processing_id,
                "document-id": document_id,
                "time": timestamp,
                "flow": flow,
                "collection": collection,
                "tags": tags
            }
        }

        gen = manager.request(
            "librarian", request_data, None, workspace=workspace,
        )

        async for response in gen:
            break

        return AddProcessingResponse()


def main():
    parser = argparse.ArgumentParser(description='TrustGraph MCP Server')
    parser.add_argument(
        '--host', default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)',
    )
    parser.add_argument(
        '--port', type=int, default=8000,
        help='Port to bind to (default: 8000)',
    )
    parser.add_argument(
        '--websocket-url',
        default='ws://api-gateway:8088/api/v1/socket',
        help='WebSocket URL for the TrustGraph gateway',
    )
    parser.add_argument(
        '--auth-issuer',
        default=os.environ.get("AUTH_ISSUER", ""),
        help='OAuth issuer URL for MCP auth metadata discovery',
    )
    parser.add_argument(
        '--auth-resource-url',
        default=os.environ.get("AUTH_RESOURCE_URL", ""),
        help='Resource server URL for OAuth protected resource metadata',
    )

    add_logging_args(parser)

    args = parser.parse_args()

    setup_logging(vars(args))

    server = McpServer(
        host=args.host,
        port=args.port,
        websocket_url=args.websocket_url,
        auth_issuer=args.auth_issuer,
        auth_resource_url=args.auth_resource_url,
    )
    server.run()


def run():
    main()


if __name__ == "__main__":
    main()
