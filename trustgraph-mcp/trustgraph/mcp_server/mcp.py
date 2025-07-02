
from contextlib import asynccontextmanager
from typing import Optional
import os
import time
from typing import AsyncGenerator, Any, Dict, List
import asyncio
import logging
import json
import uuid
from dataclasses import dataclass
from collections.abc import AsyncIterator

from mcp.server.fastmcp import FastMCP, Context
from mcp.types import TextContent
from websockets.asyncio.client import connect

from . tg_socket import WebSocketManager

# TrustGraph
from trustgraph.api import Api

@dataclass
class AppContext:
    sockets: dict[str, WebSocketManager]

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:

    """
    Manage application lifecycle with type-safe context
    """

    # Initialize on startup
    sockets = {}

    try:
        yield AppContext(sockets=sockets)
    finally:

        # Cleanup on shutdown
        logging.info("Shutting down context")

        for k, manager in sockets.items():
            logging.info(f"Closing socket for {k}")
            await manager.stop()

        logging.info("Shutdown complete")

# Create an MCP server
mcp = FastMCP(
    "TrustGraph", dependencies=["trustgraph-base"],
    host="0.0.0.0", port=8092,
    lifespan=app_lifespan,
)

default_url = os.getenv("TRUSTGRAPH_URL", 'http://localhost:8088/')

async def get_socket_manager(ctx, user):

    sockets = ctx.request_context.lifespan_context.sockets

    if user in sockets:
        logging.info("Return existing socket manager")
        return sockets[user]

    logging.info("Opening socket...")
    
    # Create manager with empty pending requests
    manager = WebSocketManager("ws://localhost:8088/api/v1/socket")
    
    # Start reader task with the proper manager
    await manager.start()
    
    sockets[user] = manager

    logging.info("Return new socket manager")
    return manager

@dataclass
class EmbeddingsResponse:
    vectors: List[List[float]]

@mcp.tool()
async def embeddings(
        text: str,
        flow_id: str | None = None,
        ctx: Context = None,
) -> EmbeddingsResponse:

    """
    Compute text embeddings
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

@dataclass
class TextCompletionResponse:
    response: str

# Add an addition tool
@mcp.tool()
async def text_completion(
        prompt: str,
        system: str | None = None,
        flow_id: str | None = None,
        ctx: Context = None,
) -> TextCompletionResponse:
    """Execute an LLM prompt"""

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

@dataclass
class GraphRagResponse:
    response: str

# Add an addition tool
@mcp.tool()
async def graph_rag(
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
    """Execute a GraphRAG question"""

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

@dataclass
class AgentResponse:
    answer: str

# Add an addition tool
@mcp.tool()
async def agent(
        question: str,
        user: str | None = None,
        collection: str | None = None,
        flow_id: str | None = None,
        ctx: Context = None,
) -> AgentResponse:
    """Execute an agent question"""

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

        print(response)

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

@mcp.tool()
async def triples_query(
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
    Query knowledge graph triples (subject-predicate-object relationships)
    All parameters are optional - omitted parameters act as wildcards
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

@mcp.tool()
async def graph_embeddings_query(
        vectors: List[List[float]],
        limit: int | None = None,
        flow_id: str | None = None,
        ctx: Context = None,
) -> GraphEmbeddingsQueryResponse:
    """
    Query graph using embedding vectors
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

@mcp.tool()
async def get_config_all(
        ctx: Context = None,
) -> ConfigResponse:
    """
    Retrieves complete configuration
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

@mcp.tool()
async def get_config(
        keys: List[Dict[str, str]],
        ctx: Context = None,
) -> ConfigGetResponse:
    """
    Retrieves specific configuration entries
    Keys should be list of dicts with 'type' and 'key' fields
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


@dataclass
class PutConfigResponse:
    pass

@mcp.tool()
async def put_config(
        values: List[Dict[str, str]],
        ctx: Context = None,
) -> PutConfigResponse:
    """
    Updates configuration values
    Values should be list of dicts with 'type', 'key', and 'value' fields
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
    
@dataclass
class DeleteConfigResponse:
    pass

@mcp.tool()
async def delete_config(
        keys: List[Dict[str, str]],
        ctx: Context = None,
) -> DeleteConfigResponse:
    """
    Deletes configuration entries
    Keys should be list of dicts with 'type' and 'key' fields
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

@dataclass
class GetPromptsResponse:
    prompts: List[str]

@mcp.tool()
async def get_prompts(
        ctx: Context = None,
) -> GetPromptsResponse:
    """
    Retrieves available prompt templates
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

    
@dataclass
class GetPromptResponse:
    prompt: Dict[str, Any]

@mcp.tool()
async def get_prompt(
        prompt_id: str,
        ctx: Context = None,
) -> GetPromptResponse:
    """
    Retrieves a specific prompt template
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

@dataclass
class GetSystemPromptResponse:
    prompt: str

@mcp.tool()
async def get_system_prompt(
        ctx: Context = None,
) -> GetSystemPromptResponse:
    """
    Retrieves system prompt configuration
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

@mcp.tool()
async def get_token_costs(
        ctx: Context = None,
) -> ConfigTokenCostsResponse:
    """
    Retrieves token cost information for different AI models
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

@mcp.tool()
async def get_knowledge_cores(
        user: str | None = None,
        ctx: Context = None,
) -> KnowledgeCoresResponse:
    """
    Retrieves list of available knowledge graph cores
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

@mcp.tool()
async def delete_kg_core(
        core_id: str,
        user: str | None = None,
        ctx: Context = None,
) -> DeleteKgCoreResponse:
    """
    Deletes a knowledge graph core
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

@mcp.tool()
async def load_kg_core(
        core_id: str,
        flow: str,
        user: str | None = None,
        collection: str | None = None,
        ctx: Context = None,
) -> LoadKgCoreResponse:
    """
    Loads a knowledge graph core
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

@mcp.tool()
async def get_kg_core(
        core_id: str,
        user: str | None = None,
        ctx: Context = None,
) -> GetKgCoreResponse:
    """
    Retrieves a knowledge graph core with streaming data
    Returns all chunks as a list
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

@mcp.tool()
async def get_flows(
        ctx: Context = None,
) -> FlowsResponse:
    """
    Retrieves list of available flows
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

@mcp.tool()
async def get_flow(
        flow_id: str,
        ctx: Context = None,
) -> FlowResponse:
    """
    Retrieves definition of a specific flow
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

@mcp.tool()
async def get_flow_classes(
        ctx: Context = None,
) -> FlowClassesResponse:
    """
    Retrieves list of available flow classes (templates)
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

@mcp.tool()
async def get_flow_class(
        class_name: str,
        ctx: Context = None,
) -> FlowClassResponse:
    """
    Retrieves definition of a specific flow class
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

@mcp.tool()
async def start_flow(
        flow_id: str,
        class_name: str,
        description: str,
        ctx: Context = None,
) -> StartFlowResponse:
    """
    Starts a new flow instance
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

@mcp.tool()
async def stop_flow(
        flow_id: str,
        ctx: Context = None,
) -> StopFlowResponse:
    """
    Stops a running flow instance
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

@mcp.tool()
async def get_documents(
        user: str | None = None,
        ctx: Context = None,
) -> DocumentsResponse:
    """
    Retrieves list of all documents in the system
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

@mcp.tool()
async def get_processing(
        user: str | None = None,
        ctx: Context = None,
) -> ProcessingResponse:
    """
    Retrieves list of documents currently being processed
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

@mcp.tool()
async def load_document(
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
    Uploads a document to the library with full metadata
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

@mcp.tool()
async def remove_document(
        document_id: str,
        user: str | None = None,
        ctx: Context = None,
) -> RemoveDocumentResponse:
    """
    Removes a document from the library
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

@mcp.tool()
async def add_processing(
        processing_id: str,
        document_id: str,
        flow: str,
        user: str | None = None,
        collection: str | None = None,
        tags: List[str] | None = None,
        ctx: Context = None,
) -> AddProcessingResponse:
    """
    Adds a document to the processing queue
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

def run():
    mcp.run(transport="streamable-http")

