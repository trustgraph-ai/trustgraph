
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
    def __init__(self, context, collection=None):
        self.context = context
        self.collection = collection  # For multi-tenant scenarios
    
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
        
        result = await client.structured_query(
            arguments.get("question")
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
