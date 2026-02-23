
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
