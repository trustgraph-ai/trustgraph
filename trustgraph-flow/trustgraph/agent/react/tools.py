
import json
import logging
from .types import Argument

# Module logger
logger = logging.getLogger(__name__)

# This tool implementation knows how to put a question to the graph RAG
# service
class KnowledgeQueryImpl:
    def __init__(self, context, collection=None):
        self.context = context
        self.collection = collection
    
    @staticmethod
    def get_arguments():
        return [
            Argument(
                name="question",
                type="string",
                description="The question to ask the knowledge base"
            )
        ]
    
    async def invoke(self, **arguments):
        client = self.context("graph-rag-request")
        logger.debug("Graph RAG question...")
        return await client.rag(
            arguments.get("question"),
            collection=self.collection if self.collection else "default"
        )

# This tool implementation knows how to do text completion.  This uses
# the prompt service, rather than talking  to TextCompletion directly.
class TextCompletionImpl:
    def __init__(self, context):
        self.context = context
    
    @staticmethod
    def get_arguments():
        return [
            Argument(
                name="question",
                type="string",
                description="The text prompt or question for completion"
            )
        ]
    
    async def invoke(self, **arguments):
        client = self.context("prompt-request")
        logger.debug("Prompt question...")
        return await client.question(
            arguments.get("question")
        )

# This tool implementation knows how to do MCP tool invocation.  This uses
# the mcp-tool service.
class McpToolImpl:

    def __init__(self, context, mcp_tool_id, arguments=None):
        self.context = context
        self.mcp_tool_id = mcp_tool_id
        self.arguments = arguments or []
    
    def get_arguments(self):
        # Return configured arguments if available, otherwise empty list for backward compatibility
        return self.arguments

    async def invoke(self, **arguments):

        client = self.context("mcp-tool-request")

        logger.debug(f"MCP tool invocation: {self.mcp_tool_id}...")
        output = await client.invoke(
            name = self.mcp_tool_id,
            parameters = arguments,  # Pass the actual arguments
        )

        logger.debug(f"MCP tool output: {output}")

        if isinstance(output, str):
            return output
        else:
            return json.dumps(output)


# This tool implementation knows how to query structured data using natural language
class StructuredQueryImpl:
    def __init__(self, context, collection=None, user=None):
        self.context = context
        self.collection = collection  # For multi-tenant scenarios
        self.user = user              # User context for multi-tenancy
    
    @staticmethod
    def get_arguments():
        return [
            Argument(
                name="question",
                type="string", 
                description="Natural language question about structured data (tables, databases, etc.)"
            )
        ]
    
    async def invoke(self, **arguments):
        client = self.context("structured-query-request")
        logger.debug("Structured query question...")
        
        # Get user from client context if available, otherwise use instance user or default
        user = getattr(client, '_current_user', self.user or "trustgraph")
        
        result = await client.structured_query(
            question=arguments.get("question"),
            user=user,
            collection=self.collection or "default"
        )
        
        # Format the result for the agent
        if isinstance(result, dict):
            if result.get("error"):
                return f"Error: {result['error']['message']}"
            elif result.get("data"):
                # Pretty format JSON data for agent consumption
                return json.dumps(result["data"], indent=2)
            else:
                return "No data returned"
        else:
            return str(result)


# This tool implementation knows how to query row embeddings for semantic search
class RowEmbeddingsQueryImpl:
    def __init__(self, context, schema_name, collection=None, user=None, index_name=None, limit=10):
        self.context = context
        self.schema_name = schema_name
        self.collection = collection
        self.user = user
        self.index_name = index_name  # Optional: filter to specific index
        self.limit = limit  # Max results to return

    @staticmethod
    def get_arguments():
        return [
            Argument(
                name="query",
                type="string",
                description="Text to search for semantically similar values in the structured data index"
            )
        ]

    async def invoke(self, **arguments):
        # First get embeddings for the query text
        embeddings_client = self.context("embeddings-request")
        logger.debug("Getting embeddings for row query...")

        query_text = arguments.get("query")
        vectors = await embeddings_client.embed(query_text)

        # Now query row embeddings
        client = self.context("row-embeddings-query-request")
        logger.debug("Row embeddings query...")

        # Get user from client context if available
        user = getattr(client, '_current_user', self.user or "trustgraph")

        matches = await client.row_embeddings_query(
            vectors=vectors,
            schema_name=self.schema_name,
            user=user,
            collection=self.collection or "default",
            index_name=self.index_name,
            limit=self.limit
        )

        # Format results for agent consumption
        if not matches:
            return "No matching records found"

        results = []
        for match in matches:
            result = f"- {match['index_name']}: {', '.join(match['index_value'])} (score: {match['score']:.3f})"
            results.append(result)

        return "Matching records:\n" + "\n".join(results)


# This tool implementation knows how to execute prompt templates
class PromptImpl:
    def __init__(self, context, template_id, arguments=None):
        self.context = context
        self.template_id = template_id
        self.arguments = arguments or []  # These come from config
    
    def get_arguments(self):
        # For prompt tools, arguments are defined in configuration
        return self.arguments
    
    async def invoke(self, **arguments):
        client = self.context("prompt-request")
        logger.debug(f"Prompt template invocation: {self.template_id}...")
        return await client.prompt(
            id=self.template_id,
            variables=arguments
        )


# This tool implementation invokes a dynamically configured tool service
class ToolServiceImpl:
    """
    Implementation for dynamically pluggable tool services.

    Tool services are external Pulsar services that can be invoked as agent tools.
    The service is configured via a tool-service descriptor that defines the topic,
    and a tool descriptor that provides config values and argument definitions.
    """

    def __init__(self, context, service_topic, config_values=None, arguments=None, processor=None):
        """
        Initialize a tool service implementation.

        Args:
            context: The context function (provides user info)
            service_topic: The base topic name for the service
            config_values: Dict of config values (e.g., {"collection": "customers"})
            arguments: List of Argument objects defining the tool's parameters
            processor: The Processor instance (for pubsub access)
        """
        self.context = context
        self.service_topic = service_topic
        self.config_values = config_values or {}
        self.arguments = arguments or []
        self.processor = processor
        self._client = None

    def get_arguments(self):
        return self.arguments

    async def _get_or_create_client(self):
        """Get or create the tool service client."""
        if self._client is not None:
            return self._client

        # Check if processor already has a client for this topic
        if self.service_topic in self.processor.tool_service_clients:
            self._client = self.processor.tool_service_clients[self.service_topic]
            return self._client

        # Import here to avoid circular imports
        from ....base.tool_service_client import ToolServiceClient
        from ....base.metrics import ProducerMetrics, SubscriberMetrics
        from ....schema import ToolServiceRequest, ToolServiceResponse
        import uuid

        request_topic = f"{self.service_topic}-request"
        response_topic = f"{self.service_topic}-response"

        request_metrics = ProducerMetrics(
            processor=self.processor.id,
            flow="tool-service",
            name=request_topic
        )
        response_metrics = SubscriberMetrics(
            processor=self.processor.id,
            flow="tool-service",
            name=response_topic
        )

        # Create unique subscription for responses
        subscription = f"{self.processor.id}--tool-service--{self.service_topic}--{uuid.uuid4()}"

        self._client = ToolServiceClient(
            backend=self.processor.pubsub,
            subscription=subscription,
            consumer_name=self.processor.id,
            request_topic=request_topic,
            request_schema=ToolServiceRequest,
            request_metrics=request_metrics,
            response_topic=response_topic,
            response_schema=ToolServiceResponse,
            response_metrics=response_metrics,
        )

        # Start the client
        await self._client.start()

        # Register for cleanup
        self.processor.tool_service_clients[self.service_topic] = self._client

        logger.debug(f"Created tool service client for {self.service_topic}")
        return self._client

    async def invoke(self, **arguments):
        logger.debug(f"Tool service invocation: {self.service_topic}...")
        logger.debug(f"Config: {self.config_values}")
        logger.debug(f"Arguments: {arguments}")

        # Get user from context if available
        user = "trustgraph"
        if hasattr(self.context, '_user'):
            user = self.context._user

        # Get or create the client
        client = await self._get_or_create_client()

        # Call the tool service
        response = await client.call(
            user=user,
            config=self.config_values,
            arguments=arguments,
        )

        logger.debug(f"Tool service response: {response}")

        if isinstance(response, str):
            return response
        else:
            return json.dumps(response)
