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
from dataclasses import dataclass
from collections.abc import AsyncIterator
from functools import partial

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import TextContent
from websockets.asyncio.client import connect

from trustgraph.base.logging import add_logging_args, setup_logging

from . tg_socket import WebSocketManager

@dataclass
class AppContext:
    sockets: dict[str, WebSocketManager]
    websocket_url: str

@asynccontextmanager
async def app_lifespan(server: FastMCP, websocket_url: str = "ws://api-gateway:8088/api/v1/socket") -> AsyncIterator[AppContext]:

    """
    Manage application lifecycle with type-safe context
    """

    # Initialize on startup
    sockets = {}

    try:
        yield AppContext(sockets=sockets, websocket_url=websocket_url)
    finally:

        # Cleanup on shutdown
        logging.info("Shutting down context")

        for k, manager in sockets.items():
            logging.info(f"Closing socket for {k}")
            await manager.stop()

        logging.info("Shutdown complete")

async def get_socket_manager(ctx, user):

    lifespan_context = ctx.request_context.lifespan_context
    sockets = lifespan_context.sockets
    websocket_url = lifespan_context.websocket_url

    if user in sockets:
        logging.info("Return existing socket manager")
        return sockets[user]

    logging.info(f"Opening socket to {websocket_url}...")
    
    # Create manager with empty pending requests
    manager = WebSocketManager(websocket_url)
    
    # Start reader task with the proper manager
    await manager.start()
    
    sockets[user] = manager

    logging.info("Return new socket manager")
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
class GetPromptsResponse:
    prompts: List[str]
    
@dataclass
class GetPromptResponse:
    prompt: Dict[str, Any]

@dataclass
class GetSystemPromptResponse:
    prompt: str

class McpServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8000, websocket_url: str = "ws://api-gateway:8088/api/v1/socket"):
        self.host = host
        self.port = port
        self.websocket_url = websocket_url
        
        # Create a partial function to pass websocket_url to app_lifespan
        lifespan_with_url = partial(app_lifespan, websocket_url=websocket_url)
        
        self.mcp = FastMCP(
            "TrustGraph", dependencies=["trustgraph-base"],
            host=self.host, port=self.port,
            lifespan=lifespan_with_url,
        )
        self._register_tools()
    
    def _register_tools(self):
        """Register all MCP tools"""
        # Register all the tools that were previously registered globally
        self.mcp.tool()(self.embeddings)
        self.mcp.tool()(self.text_completion)
        self.mcp.tool()(self.graph_rag)
        self.mcp.tool()(self.agent)
        self.mcp.tool()(self.triples_query)
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

    async def embeddings(
            self,
            text: str,
            flow_id: str | None = None,
            ctx: Context = None,
    ) -> EmbeddingsResponse:
        """
        Generate vector embeddings for the given text using TrustGraph's embedding models.
        
        This tool converts text into high-dimensional vectors that capture semantic meaning,
        enabling similarity searches, clustering, and other vector-based operations.
        
        Args:
            text: The input text to convert into embeddings. Can be a sentence, paragraph, 
                  or document. The text will be processed by the configured embedding model.
            flow_id: Optional flow identifier to use for processing (default: "default").
                     Different flows may use different embedding models or configurations.
        
        Returns:
            EmbeddingsResponse containing a list of vectors. Each vector is a list of floats
            representing the text's semantic embedding in the model's vector space.
        
        Example usage:
            - Convert a query into embeddings for similarity search
            - Generate embeddings for documents before storing them
            - Create embeddings for comparison with existing knowledge
        """

        logging.info("Embeddings request made")

        if flow_id is None: flow_id = "default"

        manager = await get_socket_manager(ctx, "trustgraph")

        if ctx is None:
            raise RuntimeError("No context provided")

        await ctx.session.send_log_message(
            level="info",
            data=f"Computing embeddings via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        # Send websocket request
        request_data = {"text": text}
        logging.info("making request")

        gen = manager.request("embeddings", request_data, flow_id)

        async for response in gen:

            # Extract vectors from response
            vectors = response.get("vectors", [[]])
            break
        
        return EmbeddingsResponse(vectors=vectors)

    async def text_completion(
            self,
            prompt: str,
            system: str | None = None,
            flow_id: str | None = None,
            ctx: Context = None,
    ) -> TextCompletionResponse:
        """
        Generate text completions using TrustGraph's language models.
        
        This tool sends prompts to configured language models and returns generated text.
        It supports both user prompts and system instructions for controlling generation.
        
        Args:
            prompt: The main prompt or question to send to the language model.
                    This is the primary input that guides the model's response.
            system: Optional system prompt that sets the context, role, or behavior
                    for the AI assistant (e.g., "You are a helpful coding assistant").
                    System prompts influence how the model interprets and responds.
            flow_id: Optional flow identifier (default: "default"). Different flows
                     may use different models, parameters, or processing pipelines.
        
        Returns:
            TextCompletionResponse containing the generated text response from the model.
        
        Example usage:
            - Ask questions and get AI-generated answers
            - Generate code, documentation, or creative content
            - Perform text analysis, summarization, or transformation tasks
            - Use system prompts to control tone, style, or domain expertise
        """

        if system is None: system = ""
        if flow_id is None: flow_id = "default"

        if ctx is None:
            raise RuntimeError("No context provided")

        # Use websocket if context is available
        logging.info("Text completion request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

        await ctx.session.send_log_message(
            level="info",
            data=f"Generating text completion via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        # Send websocket request
        request_data = {"system": system, "prompt": prompt}

        gen = manager.request("text-completion", request_data, flow_id)

        async for response in gen:

            # Extract vectors from response
            text = response.get("response", "")
            break
        
        return TextCompletionResponse(response=text)

    async def graph_rag(
            self,
            question: str,
            user: str | None = None,
            collection: str | None = None,
            entity_limit: int | None = None,
            triple_limit: int | None = None,
            max_subgraph_size: int | None = None,
            max_path_length: int | None = None,
            flow_id: str | None = None,
            ctx: Context = None,
    ) -> GraphRagResponse:
        """
        Perform Graph-based Retrieval Augmented Generation (GraphRAG) queries.
        
        GraphRAG combines knowledge graph traversal with language model generation to provide
        contextually rich answers. It explores relationships between entities to build relevant
        context before generating responses.
        
        Args:
            question: The question or query to answer using the knowledge graph.
                      The system will find relevant entities and relationships to inform the response.
            user: User identifier for access control and personalization (default: "trustgraph").
            collection: Knowledge collection to query (default: "default").
                        Different collections may contain domain-specific knowledge.
            entity_limit: Maximum number of entities to retrieve during graph traversal.
                          Higher limits provide more context but increase processing time.
            triple_limit: Maximum number of relationship triples to consider.
                          Controls the depth of relationship exploration.
            max_subgraph_size: Maximum size of the subgraph to extract for context.
                               Larger subgraphs provide richer context but use more resources.
            max_path_length: Maximum path length to traverse in the knowledge graph.
                             Longer paths can discover distant but relevant relationships.
            flow_id: Processing flow to use (default: "default").
        
        Returns:
            GraphRagResponse containing the generated answer informed by knowledge graph context.
        
        Example usage:
            - Answer complex questions requiring multi-hop reasoning
            - Explore relationships between entities in your knowledge base
            - Generate responses grounded in structured knowledge
            - Perform research queries across connected information
        """

        if user is None: user = "trustgraph"
        if collection is None: collection = "default"
        if flow_id is None: flow_id = "default"

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("GraphRAG request made via websocket")

        manager = await get_socket_manager(ctx, user)

        await ctx.session.send_log_message(
            level="info",
            data=f"Processing GraphRAG query via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        # Build request data with all parameters
        request_data = {
            "query": question
        }

        if user: request_data["user"] = user
        if collection: request_data["collection"] = collection
        if entity_limit: request_data["entity_limit"] = entity_limit
        if triple_limit: request_data["triple_limit"] = triple_limit
        if max_subgraph_size: request_data["max_subgraph_size"] = max_subgraph_size
        if max_path_length: request_data["max_path_length"] = max_path_length

        gen = manager.request("graph-rag", request_data, flow_id)

        async for response in gen:

            # Extract vectors from response
            text = response.get("response", "")
            break
        
        return GraphRagResponse(response=text)

    async def agent(
            self,
            question: str,
            user: str | None = None,
            collection: str | None = None,
            flow_id: str | None = None,
            ctx: Context = None,
    ) -> AgentResponse:
        """
        Execute intelligent agent queries with reasoning and tool usage capabilities.
        
        The agent can perform complex multi-step reasoning, use tools, and provide
        detailed thought processes. It's designed for tasks requiring planning,
        analysis, and iterative problem-solving.
        
        Args:
            question: The question or task for the agent to solve. Can be complex
                      queries requiring multiple steps, analysis, or tool usage.
            user: User identifier for personalization and access control (default: "trustgraph").
            collection: Knowledge collection the agent can access (default: "default").
                        Determines what information and tools are available.
            flow_id: Agent workflow to use (default: "default"). Different flows
                     may have different capabilities, tools, or reasoning strategies.
        
        Returns:
            AgentResponse containing the final answer after the agent's reasoning process.
            During execution, you'll see intermediate thoughts and observations.
        
        Example usage:
            - Solve complex analytical problems requiring multiple steps
            - Perform research tasks across multiple information sources
            - Handle queries that need tool usage and decision-making
            - Get detailed explanations of reasoning processes
        
        Note: This tool provides real-time updates on the agent's thinking process
        through log messages, so you can follow its reasoning steps.
        """

        if user is None: user = "trustgraph"
        if collection is None: collection = "default"
        if flow_id is None: flow_id = "default"

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Agent request made via websocket")

        manager = await get_socket_manager(ctx, user)

        await ctx.session.send_log_message(
            level="info",
            data=f"Processing agent query via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        # Build request data with all parameters
        request_data = {
            "question": question
        }

        if user: request_data["user"] = user
        if collection: request_data["collection"] = collection

        gen = manager.request("agent", request_data, flow_id)

        async for response in gen:

            logging.debug(f"Agent response: {response}")

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

            # Extract vectors from response
            if "answer" in response:
                answer = response.get("answer", "")
                return AgentResponse(answer=answer)

    async def triples_query(
            self,
            s_v: str | None = None,
            s_e: bool | None = None,
            p_v: str | None = None,
            p_e: bool | None = None,
            o_v: str | None = None,
            o_e: bool | None = None,
            limit: int | None = None,
            flow_id: str | None = None,
            ctx: Context = None,
    ) -> TriplesQueryResponse:
        """
        Query knowledge graph triples using subject-predicate-object patterns.
        
        Knowledge graphs store information as triples (subject, predicate, object).
        This tool allows flexible querying by specifying any combination of these
        components, with wildcards for unspecified parts.
        
        Args:
            s_v: Subject value to match (e.g., "John", "Apple Inc."). Leave None for wildcard.
            s_e: Whether subject should be treated as an entity (True) or literal (False).
            p_v: Predicate/relationship value (e.g., "works_for", "type_of"). Leave None for wildcard.
            p_e: Whether predicate should be treated as an entity (True) or literal (False).
            o_v: Object value to match (e.g., "Engineer", "Company"). Leave None for wildcard.
            o_e: Whether object should be treated as an entity (True) or literal (False).
            limit: Maximum number of triples to return (default: 20).
            flow_id: Processing flow identifier (default: "default").
        
        Returns:
            TriplesQueryResponse containing matching triples from the knowledge graph.
        
        Example queries:
            - Find all relationships for an entity: s_v="John", others None
            - Find all instances of a relationship: p_v="works_for", others None
            - Find specific facts: s_v="John", p_v="works_for", o_v=None
            - Explore entity types: p_v="type_of", others None
        
        Use this for:
            - Exploring knowledge graph structure
            - Finding specific facts or relationships
            - Discovering connections between entities
            - Validating or debugging knowledge content
        """

        if flow_id is None: flow_id = "default"
        if limit is None: limit = 20

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Triples query request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

        await ctx.session.send_log_message(
            level="info",
            data=f"Processing triples query via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        # Build request data with Value objects
        request_data = {
            "limit": limit
        }

        # Add subject if provided
        if s_v is not None:
            request_data["s"] = {"v": s_v, "e": s_e }

        # Add predicate if provided
        if p_v is not None:
            request_data["p"] = {"v": p_v, "e": p_e }

        # Add object if provided
        if o_v is not None:
            request_data["o"] = {"v": o_v, "e": o_e }

        gen = manager.request("triples", request_data, flow_id)

        async for response in gen:
            # Extract response data
            triples = response.get("response", [])
            break
        
        return TriplesQueryResponse(triples=triples)

    async def graph_embeddings_query(
            self,
            vectors: List[List[float]],
            limit: int | None = None,
            flow_id: str | None = None,
            ctx: Context = None,
    ) -> GraphEmbeddingsQueryResponse:
        """
        Find entities in the knowledge graph using vector similarity search.
        
        This tool performs semantic search by comparing embedding vectors to find
        the most similar entities in the knowledge graph. It's useful for finding
        conceptually related information even when exact text matches don't exist.
        
        Args:
            vectors: List of embedding vectors to search with. Each vector should be
                     a list of floats representing semantic embeddings (typically from
                     the embeddings tool). Multiple vectors can be provided for batch queries.
            limit: Maximum number of similar entities to return (default: 20).
                   Higher limits provide more results but may include less relevant matches.
            flow_id: Processing flow identifier (default: "default").
        
        Returns:
            GraphEmbeddingsQueryResponse containing entities ranked by similarity to the
            input vectors, along with similarity scores and entity metadata.
        
        Example workflow:
            1. Use the 'embeddings' tool to convert text to vectors
            2. Use this tool to find similar entities in the knowledge graph
            3. Explore the returned entities for relevant information
        
        Use this for:
            - Semantic search across knowledge entities
            - Finding conceptually similar content
            - Discovering related entities without exact keyword matches
            - Building recommendation systems based on entity similarity
        """

        if flow_id is None: flow_id = "default"
        if limit is None: limit = 20

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Graph embeddings query request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

        await ctx.session.send_log_message(
            level="info",
            data=f"Processing graph embeddings query via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        # Build request data
        request_data = {
            "vectors": vectors,
            "limit": limit
        }

        gen = manager.request("graph-embeddings", request_data, flow_id)

        async for response in gen:
            # Extract entities from response
            entities = response.get("entities", [])
            break
        
        return GraphEmbeddingsQueryResponse(entities=entities)

    async def get_config_all(
            self,
            ctx: Context = None,
    ) -> ConfigResponse:
        """
        Retrieve the complete TrustGraph system configuration.
        
        This tool returns all configuration settings for the TrustGraph system,
        including model configurations, API keys, flow definitions, and system parameters.
        
        Returns:
            ConfigResponse containing the full configuration as a nested dictionary
            with all system settings, organized by category (e.g., models, flows, storage).
        
        Use this for:
            - Inspecting current system configuration
            - Debugging configuration issues
            - Understanding available models and settings
            - Auditing system setup and parameters
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get config all request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

        await ctx.session.send_log_message(
            level="info",
            data=f"Retrieving all configuration via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        request_data = {
            "operation": "config"
        }

        gen = manager.request("config", request_data, None)

        async for response in gen:
            config = response.get("config", {})
            break
        
        return ConfigResponse(config=config)

    async def get_config(
            self,
            keys: List[Dict[str, str]],
            ctx: Context = None,
    ) -> ConfigGetResponse:
        """
        Retrieve specific configuration values by key.
        
        This tool allows you to fetch specific configuration settings without
        retrieving the entire configuration. Useful for checking particular
        settings or API keys.
        
        Args:
            keys: List of configuration keys to retrieve. Each key should be a dict with:
                  - 'type': Configuration category (e.g., 'llm', 'embeddings', 'storage')
                  - 'key': Specific setting name within that category
        
        Returns:
            ConfigGetResponse containing the requested configuration values.
        
        Example keys:
            - {'type': 'llm', 'key': 'openai.model'}
            - {'type': 'embeddings', 'key': 'default.model'}
            - {'type': 'storage', 'key': 'database.url'}
        
        Use this for:
            - Checking specific model configurations
            - Validating API key settings
            - Inspecting individual system parameters
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get config request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

        await ctx.session.send_log_message(
            level="info",
            data=f"Retrieving specific configuration via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        request_data = {
            "operation": "get",
            "keys": keys
        }

        gen = manager.request("config", request_data, None)

        async for response in gen:
            values = response.get("values", [])
            break
        
        return ConfigGetResponse(values=values)

    async def put_config(
            self,
            values: List[Dict[str, str]],
            ctx: Context = None,
    ) -> PutConfigResponse:
        """
        Update system configuration values.
        
        This tool allows you to modify TrustGraph system settings, such as
        model parameters, API keys, and system behavior configurations.
        
        Args:
            values: List of configuration updates. Each update should be a dict with:
                    - 'type': Configuration category (e.g., 'llm', 'embeddings')
                    - 'key': Specific setting name to update
                    - 'value': New value for the setting
        
        Returns:
            PutConfigResponse confirming the configuration update.
        
        Example updates:
            - {'type': 'llm', 'key': 'openai.model', 'value': 'gpt-4'}
            - {'type': 'embeddings', 'key': 'batch_size', 'value': '100'}
        
        Use this for:
            - Switching between different models
            - Updating API credentials
            - Modifying system behavior parameters
            - Configuring processing settings
        
        Note: Configuration changes may require system restart to take effect.
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Put config request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

        await ctx.session.send_log_message(
            level="info",
            data=f"Updating configuration via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        request_data = {
            "operation": "put",
            "values": values
        }

        gen = manager.request("config", request_data, None)

        async for response in gen:
            return PutConfigResponse()

    async def delete_config(
            self,
            keys: List[Dict[str, str]],
            ctx: Context = None,
    ) -> DeleteConfigResponse:
        """
        Delete specific configuration entries from the system.
        
        This tool removes configuration settings, reverting them to system defaults
        or disabling specific features.
        
        Args:
            keys: List of configuration keys to delete. Each key should be a dict with:
                  - 'type': Configuration category (e.g., 'llm', 'embeddings')
                  - 'key': Specific setting name to remove
        
        Returns:
            DeleteConfigResponse confirming the deletion.
        
        Use this for:
            - Removing custom model configurations
            - Clearing API credentials
            - Resetting settings to defaults
            - Cleaning up obsolete configurations
        
        Warning: Deleting essential configuration may cause system functionality
        to be disabled until properly reconfigured.
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Delete config request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

        await ctx.session.send_log_message(
            level="info",
            data=f"Deleting configuration via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        request_data = {
            "operation": "delete",
            "keys": keys
        }

        gen = manager.request("config", request_data, None)

        async for response in gen:
            return DeleteConfigResponse()

    async def get_prompts(
            self,
            ctx: Context = None,
    ) -> GetPromptsResponse:
        """
        List all available prompt templates in the system.
        
        Prompt templates are reusable prompts that can be used with language models
        for consistent behavior across different queries and use cases.
        
        Returns:
            GetPromptsResponse containing a list of available prompt template IDs.
            Each ID can be used with get_prompt to retrieve the full template.
        
        Use this for:
            - Discovering available prompt templates
            - Exploring pre-configured prompts for different tasks
            - Finding templates for specific use cases
            - Understanding what prompt options are available
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get prompts request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

        await ctx.session.send_log_message(
            level="info",
            data=f"Retrieving prompt templates via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        # First get all config
        request_data = {
            "operation": "config"
        }

        gen = manager.request("config", request_data, None)

        async for response in gen:
            config = response.get("config", {})
            prompt_config = config.get("prompt", {})
            template_index = prompt_config.get("template-index", "[]")
            prompts = json.loads(template_index) if isinstance(template_index, str) else template_index
            return GetPromptsResponse(prompts=prompts)

    async def get_prompt(
            self,
            prompt_id: str,
            ctx: Context = None,
    ) -> GetPromptResponse:
        """
        Retrieve a specific prompt template by ID.
        
        Prompt templates contain structured prompts with placeholders, instructions,
        and metadata for specific tasks or domains.
        
        Args:
            prompt_id: The unique identifier of the prompt template to retrieve.
                       Use get_prompts to see available template IDs.
        
        Returns:
            GetPromptResponse containing the complete prompt template with its
            structure, placeholders, and usage instructions.
        
        Use this for:
            - Examining prompt template structure
            - Understanding how to use specific templates
            - Copying or modifying existing prompts
            - Learning prompt engineering patterns
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get prompt request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

        await ctx.session.send_log_message(
            level="info",
            data=f"Retrieving prompt template '{prompt_id}' via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        # First get all config
        request_data = {
            "operation": "config"
        }

        gen = manager.request("config", request_data, None)

        async for response in gen:
            config = response.get("config", {})
            prompt_config = config.get("prompt", {})
            template_key = f"template.{prompt_id}"
            template_data = prompt_config.get(template_key, "{}")
            prompt = json.loads(template_data) if isinstance(template_data, str) else template_data
            return GetPromptResponse(prompt=prompt)

    async def get_system_prompt(
            self,
            ctx: Context = None,
    ) -> GetSystemPromptResponse:
        """
        Retrieve the current system prompt configuration.
        
        The system prompt defines the default behavior, personality, and instructions
        for language models across the TrustGraph system.
        
        Returns:
            GetSystemPromptResponse containing the system prompt text and configuration.
        
        Use this for:
            - Understanding default AI behavior settings
            - Checking current system-wide prompt configuration
            - Auditing AI personality and instruction settings
            - Debugging unexpected AI responses
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get system prompt request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

        await ctx.session.send_log_message(
            level="info",
            data=f"Retrieving system prompt via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        # First get all config
        request_data = {
            "operation": "config"
        }

        gen = manager.request("config", request_data, None)

        async for response in gen:
            config = response.get("config", {})
            prompt_config = config.get("prompt", {})
            system_data = prompt_config.get("system", "{}")
            system_prompt = json.loads(system_data) if isinstance(system_data, str) else system_data
            return GetSystemPromptResponse(prompt=system_prompt)

    async def get_token_costs(
            self,
            ctx: Context = None,
    ) -> ConfigTokenCostsResponse:
        """
        Retrieve token pricing information for all configured AI models.
        
        This tool provides cost information for input and output tokens across
        different language models, helping with budget planning and cost optimization.
        
        Returns:
            ConfigTokenCostsResponse containing pricing data for each model including:
            - Model name/identifier
            - Input token cost (per token)
            - Output token cost (per token)
        
        Use this for:
            - Estimating costs for different models
            - Choosing cost-effective models for tasks
            - Budget planning and cost analysis
            - Monitoring and optimizing AI spending
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get token costs request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

        await ctx.session.send_log_message(
            level="info",
            data=f"Retrieving token costs via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        request_data = {
            "operation": "getvalues",
            "type": "token-costs"
        }

        gen = manager.request("config", request_data, None)

        async for response in gen:
            values = response.get("values", [])
            # Transform to match TypeScript API format
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
            user: str | None = None,
            ctx: Context = None,
    ) -> KnowledgeCoresResponse:
        """
        List all available knowledge graph cores for a user.
        
        Knowledge cores are packaged collections of structured knowledge that can
        be loaded into the system for querying and reasoning. They contain entities,
        relationships, and facts organized as knowledge graphs.
        
        Args:
            user: User identifier to list cores for (default: "trustgraph").
                  Different users may have access to different knowledge cores.
        
        Returns:
            KnowledgeCoresResponse containing a list of available knowledge core IDs.
        
        Use this for:
            - Discovering available knowledge collections
            - Understanding what knowledge domains are accessible
            - Planning which cores to load for specific tasks
            - Managing knowledge resources
        """

        if user is None: user = "trustgraph"

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get knowledge cores request made via websocket")

        manager = await get_socket_manager(ctx, user)

        await ctx.session.send_log_message(
            level="info",
            data=f"Retrieving knowledge graph cores via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        request_data = {
            "operation": "list-kg-cores",
            "user": user
        }

        gen = manager.request("knowledge", request_data, None)

        async for response in gen:
            ids = response.get("ids", [])
            break
        
        return KnowledgeCoresResponse(ids=ids)

    async def delete_kg_core(
            self,
            core_id: str,
            user: str | None = None,
            ctx: Context = None,
    ) -> DeleteKgCoreResponse:
        """
        Permanently delete a knowledge graph core.
        
        This operation removes a knowledge core from storage. Use with caution
        as this action cannot be undone.
        
        Args:
            core_id: Unique identifier of the knowledge core to delete.
            user: User identifier (default: "trustgraph"). Only cores owned
                  by this user can be deleted.
        
        Returns:
            DeleteKgCoreResponse confirming the deletion.
        
        Use this for:
            - Cleaning up obsolete knowledge cores
            - Removing test or experimental data
            - Managing storage space
            - Maintaining organized knowledge collections
        
        Warning: This permanently deletes the knowledge core and all its data.
        """

        if user is None: user = "trustgraph"

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Delete KG core request made via websocket")

        manager = await get_socket_manager(ctx, user)

        await ctx.session.send_log_message(
            level="info",
            data=f"Deleting knowledge graph core '{core_id}' via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        request_data = {
            "operation": "delete-kg-core",
            "id": core_id,
            "user": user
        }

        gen = manager.request("knowledge", request_data, None)

        async for response in gen:
            break
        
        return DeleteKgCoreResponse()

    async def load_kg_core(
            self,
            core_id: str,
            flow: str,
            user: str | None = None,
            collection: str | None = None,
            ctx: Context = None,
    ) -> LoadKgCoreResponse:
        """
        Load a knowledge graph core into the active system for querying.
        
        This operation makes a knowledge core available for GraphRAG queries,
        triple searches, and other knowledge-based operations.
        
        Args:
            core_id: Unique identifier of the knowledge core to load.
            flow: Processing flow to use for loading the core. Different flows
                  may apply different processing, indexing, or optimization steps.
            user: User identifier (default: "trustgraph").
            collection: Target collection name (default: "default"). The loaded
                        knowledge will be available under this collection name.
        
        Returns:
            LoadKgCoreResponse confirming the core has been loaded.
        
        Use this for:
            - Making knowledge cores available for queries
            - Switching between different knowledge domains
            - Loading domain-specific knowledge for tasks
            - Preparing knowledge for GraphRAG operations
        """

        if user is None: user = "trustgraph"
        if collection is None: collection = "default"

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Load KG core request made via websocket")

        manager = await get_socket_manager(ctx, user)

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
            "user": user,
            "collection": collection
        }

        gen = manager.request("knowledge", request_data, None)

        async for response in gen:
            break
        
        return LoadKgCoreResponse()

    async def get_kg_core(
            self,
            core_id: str,
            user: str | None = None,
            ctx: Context = None,
    ) -> GetKgCoreResponse:
        """
        Download and retrieve the complete content of a knowledge graph core.
        
        This tool streams the entire content of a knowledge core, returning all
        entities, relationships, and metadata. Due to potentially large data sizes,
        the content is streamed in chunks.
        
        Args:
            core_id: Unique identifier of the knowledge core to retrieve.
            user: User identifier (default: "trustgraph").
        
        Returns:
            GetKgCoreResponse containing all chunks of the knowledge core data.
            Each chunk contains part of the knowledge graph structure.
        
        Use this for:
            - Examining knowledge core content and structure
            - Debugging knowledge graph data
            - Exporting knowledge for backup or analysis
            - Understanding the scope and quality of knowledge
        
        Note: Large knowledge cores may take significant time to download.
        Progress updates are provided through log messages during streaming.
        """

        if user is None: user = "trustgraph"

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get KG core request made via websocket")

        manager = await get_socket_manager(ctx, user)

        await ctx.session.send_log_message(
            level="info",
            data=f"Retrieving knowledge graph core '{core_id}' via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        request_data = {
            "operation": "get-kg-core",
            "id": core_id,
            "user": user
        }

        # Collect all streaming responses
        chunks = []
        gen = manager.request("knowledge", request_data, None)

        async for response in gen:
            # Check for end of stream
            if response.get("eos", False):
                await ctx.session.send_log_message(
                    level="info",
                    data=f"Completed streaming KG core data",
                    logger="notification_stream",
                    related_request_id=ctx.request_id,
                )
                break
            else:
                chunks.append(response)
                await ctx.session.send_log_message(
                    level="info",
                    data=f"Received KG core chunk ({len(chunks)} chunks so far)",
                    logger="notification_stream",
                    related_request_id=ctx.request_id,
                )
        
        return GetKgCoreResponse(chunks=chunks)

    async def get_flows(
            self,
            ctx: Context = None,
    ) -> FlowsResponse:
        """
        List all available processing flows in the system.
        
        Flows define processing pipelines for different types of operations
        (e.g., document processing, knowledge extraction, query handling).
        Each flow encapsulates a specific workflow with configured steps.
        
        Returns:
            FlowsResponse containing a list of available flow identifiers.
        
        Use this for:
            - Discovering available processing workflows
            - Understanding what processing options are available
            - Choosing appropriate flows for specific tasks
            - Planning workflow-based operations
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get flows request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

        await ctx.session.send_log_message(
            level="info",
            data=f"Retrieving available flows via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        request_data = {
            "operation": "list-flows"
        }

        gen = manager.request("flow", request_data, None)

        async for response in gen:
            flow_ids = response.get("flow-ids", [])
            break
        
        return FlowsResponse(flow_ids=flow_ids)

    async def get_flow(
            self,
            flow_id: str,
            ctx: Context = None,
    ) -> FlowResponse:
        """
        Retrieve the complete definition of a specific processing flow.
        
        This tool returns the detailed configuration, steps, and parameters
        of a processing flow, showing how it processes data and what operations it performs.
        
        Args:
            flow_id: Unique identifier of the flow to retrieve.
        
        Returns:
            FlowResponse containing the complete flow definition including:
            - Flow configuration and parameters
            - Processing steps and their order
            - Input/output specifications
            - Dependencies and requirements
        
        Use this for:
            - Understanding how specific flows work
            - Debugging flow processing issues
            - Learning flow configuration patterns
            - Customizing or duplicating flows
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get flow request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

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

        gen = manager.request("flow", request_data, None)

        async for response in gen:
            flow_data = response.get("flow", "{}")
            # Parse JSON flow definition as done in TypeScript
            flow = json.loads(flow_data) if isinstance(flow_data, str) else flow_data
            break
        
        return FlowResponse(flow=flow)

    async def get_flow_classes(
            self,
            ctx: Context = None,
    ) -> FlowClassesResponse:
        """
        List all available flow class templates.
        
        Flow classes are templates that define types of processing workflows.
        They serve as blueprints for creating specific flow instances with
        customized parameters.
        
        Returns:
            FlowClassesResponse containing a list of available flow class names.
        
        Use this for:
            - Discovering available flow templates
            - Understanding what types of processing are supported
            - Planning new flow creation
            - Exploring system capabilities
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get flow classes request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

        await ctx.session.send_log_message(
            level="info",
            data=f"Retrieving flow classes via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        request_data = {
            "operation": "list-classes"
        }

        gen = manager.request("flow", request_data, None)

        async for response in gen:
            class_names = response.get("class-names", [])
            break
        
        return FlowClassesResponse(class_names=class_names)

    async def get_flow_class(
            self,
            class_name: str,
            ctx: Context = None,
    ) -> FlowClassResponse:
        """
        Retrieve the definition of a specific flow class template.
        
        Flow classes define the structure, parameters, and capabilities of
        flow types. This tool returns the class specification including
        configurable parameters and processing logic.
        
        Args:
            class_name: Name of the flow class to retrieve.
        
        Returns:
            FlowClassResponse containing the flow class definition with:
            - Class parameters and configuration options
            - Processing capabilities and requirements
            - Usage instructions and examples
        
        Use this for:
            - Understanding flow class capabilities
            - Learning how to configure new flows
            - Troubleshooting flow creation issues
            - Exploring advanced flow features
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get flow class request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

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

        gen = manager.request("flow", request_data, None)

        async for response in gen:
            class_def_data = response.get("class-definition", "{}")
            # Parse JSON class definition as done in TypeScript
            class_definition = json.loads(class_def_data) if isinstance(class_def_data, str) else class_def_data
            break
        
        return FlowClassResponse(class_definition=class_definition)

    async def start_flow(
            self,
            flow_id: str,
            class_name: str,
            description: str,
            ctx: Context = None,
    ) -> StartFlowResponse:
        """
        Create and start a new processing flow instance.
        
        This tool creates a new flow based on a flow class template and starts
        it running. The flow will begin processing according to its configuration.
        
        Args:
            flow_id: Unique identifier for the new flow instance.
            class_name: Flow class template to use for creating the flow.
                        Use get_flow_classes to see available classes.
            description: Human-readable description of the flow's purpose.
        
        Returns:
            StartFlowResponse confirming the flow has been started.
        
        Use this for:
            - Creating new processing workflows
            - Starting automated processing tasks
            - Launching background operations
            - Initiating data processing pipelines
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Start flow request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

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

        gen = manager.request("flow", request_data, None)

        async for response in gen:
            break
        
        return StartFlowResponse()

    async def stop_flow(
            self,
            flow_id: str,
            ctx: Context = None,
    ) -> StopFlowResponse:
        """
        Stop a running flow instance.
        
        This tool gracefully stops a running flow, allowing it to complete
        current operations before shutting down.
        
        Args:
            flow_id: Unique identifier of the flow instance to stop.
        
        Returns:
            StopFlowResponse confirming the flow has been stopped.
        
        Use this for:
            - Stopping unwanted or completed flows
            - Managing system resources
            - Interrupting long-running processes
            - Maintaining flow lifecycle
        """

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Stop flow request made via websocket")

        manager = await get_socket_manager(ctx, "trustgraph")

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

        gen = manager.request("flow", request_data, None)

        async for response in gen:
            break
        
        return StopFlowResponse()

    async def get_documents(
            self,
            user: str | None = None,
            ctx: Context = None,
    ) -> DocumentsResponse:
        """
        List all documents stored in the TrustGraph document library.
        
        This tool returns metadata for all documents that have been uploaded
        to the system, including their processing status and properties.
        
        Args:
            user: User identifier to list documents for (default: "trustgraph").
                  Only documents owned by this user will be returned.
        
        Returns:
            DocumentsResponse containing metadata for each document including:
            - Document ID and title
            - Upload timestamp and user
            - MIME type and size information
            - Tags and custom metadata
            - Processing status
        
        Use this for:
            - Browsing available documents
            - Managing document collections
            - Finding documents by metadata
            - Auditing document storage
        """

        if user is None: user = "trustgraph"

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get documents request made via websocket")

        manager = await get_socket_manager(ctx, user)

        await ctx.session.send_log_message(
            level="info",
            data=f"Retrieving documents list via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        request_data = {
            "operation": "list-documents",
            "user": user
        }

        gen = manager.request("librarian", request_data, None)

        async for response in gen:
            document_metadatas = response.get("document-metadatas", [])
            break
        
        return DocumentsResponse(document_metadatas=document_metadatas)

    async def get_processing(
            self,
            user: str | None = None,
            ctx: Context = None,
    ) -> ProcessingResponse:
        """
        List all documents currently in the processing queue.
        
        This tool shows documents that are being processed or waiting to be
        processed, along with their processing status and configuration.
        
        Args:
            user: User identifier (default: "trustgraph"). Only processing
                  jobs for this user will be returned.
        
        Returns:
            ProcessingResponse containing processing metadata including:
            - Processing job ID and document ID
            - Processing flow and status
            - Target collection and user
            - Timestamp and progress information
        
        Use this for:
            - Monitoring document processing progress
            - Debugging processing issues
            - Managing processing queues
            - Understanding system workload
        """

        if user is None: user = "trustgraph"

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Get processing request made via websocket")

        manager = await get_socket_manager(ctx, user)

        await ctx.session.send_log_message(
            level="info",
            data=f"Retrieving processing list via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        request_data = {
            "operation": "list-processing",
            "user": user
        }

        gen = manager.request("librarian", request_data, None)

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
            user: str | None = None,
            ctx: Context = None,
    ) -> LoadDocumentResponse:
        """
        Upload a document to the TrustGraph document library.
        
        This tool stores documents with rich metadata for later processing,
        search, and knowledge extraction. Documents can be text files, PDFs,
        or other supported formats.
        
        Args:
            document: The document content as a string. For binary files,
                      this should be base64-encoded content.
            document_id: Optional unique identifier. If not provided, one will be generated.
            metadata: Optional list of custom metadata key-value pairs.
            mime_type: MIME type of the document (e.g., 'text/plain', 'application/pdf').
            title: Human-readable title for the document.
            comments: Optional description or notes about the document.
            tags: List of tags for categorizing and finding the document.
            user: User identifier (default: "trustgraph").
        
        Returns:
            LoadDocumentResponse confirming the document has been stored.
        
        Use this for:
            - Adding new documents to the knowledge base
            - Storing reference materials and data sources
            - Building document collections for processing
            - Importing external content for analysis
        """

        if user is None: user = "trustgraph"
        if tags is None: tags = []

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Load document request made via websocket")

        manager = await get_socket_manager(ctx, user)

        await ctx.session.send_log_message(
            level="info",
            data=f"Loading document to library via websocket...",
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
                "user": user,
                "tags": tags
            },
            "content": document
        }

        gen = manager.request("librarian", request_data, None)

        async for response in gen:
            break
        
        return LoadDocumentResponse()

    async def remove_document(
            self,
            document_id: str,
            user: str | None = None,
            ctx: Context = None,
    ) -> RemoveDocumentResponse:
        """
        Permanently remove a document from the library.
        
        This operation deletes a document and all its associated metadata.
        Use with caution as this action cannot be undone.
        
        Args:
            document_id: Unique identifier of the document to remove.
            user: User identifier (default: "trustgraph"). Only documents
                  owned by this user can be removed.
        
        Returns:
            RemoveDocumentResponse confirming the document has been deleted.
        
        Use this for:
            - Cleaning up obsolete or incorrect documents
            - Managing storage space
            - Removing sensitive or inappropriate content
            - Maintaining organized document collections
        
        Warning: This permanently deletes the document and all its metadata.
        """

        if user is None: user = "trustgraph"

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Remove document request made via websocket")

        manager = await get_socket_manager(ctx, user)

        await ctx.session.send_log_message(
            level="info",
            data=f"Removing document '{document_id}' from library via websocket...",
            logger="notification_stream",
            related_request_id=ctx.request_id,
        )

        request_data = {
            "operation": "remove-document",
            "document-id": document_id,
            "user": user
        }

        gen = manager.request("librarian", request_data, None)

        async for response in gen:
            break
        
        return RemoveDocumentResponse()

    async def add_processing(
            self,
            processing_id: str,
            document_id: str,
            flow: str,
            user: str | None = None,
            collection: str | None = None,
            tags: List[str] | None = None,
            ctx: Context = None,
    ) -> AddProcessingResponse:
        """
        Queue a document for processing through a specific workflow.
        
        This tool adds a document to the processing queue where it will be
        processed by the specified flow to extract knowledge, create embeddings,
        or perform other analysis operations.
        
        Args:
            processing_id: Unique identifier for this processing job.
            document_id: ID of the document to process (must exist in library).
            flow: Processing flow to use. Different flows perform different
                  types of analysis (e.g., knowledge extraction, summarization).
            user: User identifier (default: "trustgraph").
            collection: Target collection for processed knowledge (default: "default").
                        Results will be stored under this collection name.
            tags: Optional tags for categorizing this processing job.
        
        Returns:
            AddProcessingResponse confirming the document has been queued.
        
        Use this for:
            - Processing uploaded documents into knowledge
            - Extracting entities and relationships from text
            - Creating searchable embeddings
            - Converting documents into structured knowledge
        
        Note: Processing may take time depending on document size and flow complexity.
        Use get_processing to monitor progress.
        """

        if user is None: user = "trustgraph"
        if collection is None: collection = "default"
        if tags is None: tags = []

        if ctx is None:
            raise RuntimeError("No context provided")

        logging.info("Add processing request made via websocket")

        manager = await get_socket_manager(ctx, user)

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
                "user": user,
                "collection": collection,
                "tags": tags
            }
        }

        gen = manager.request("librarian", request_data, None)

        async for response in gen:
            break
        
        return AddProcessingResponse()

def main():
    parser = argparse.ArgumentParser(description='TrustGraph MCP Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to (default: 8000)')
    parser.add_argument('--websocket-url', default='ws://api-gateway:8088/api/v1/socket', help='WebSocket URL to connect to (default: ws://api-gateway:8088/api/v1/socket)')

    # Add logging arguments
    add_logging_args(parser)

    args = parser.parse_args()

    # Setup logging before creating server
    setup_logging(vars(args))

    # Create and run the MCP server
    server = McpServer(host=args.host, port=args.port, websocket_url=args.websocket_url)
    server.run()

def run():
    """Legacy function for backward compatibility"""
    main()

if __name__ == "__main__":
    main()

