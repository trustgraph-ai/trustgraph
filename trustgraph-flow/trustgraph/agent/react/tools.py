
import json

# This tool implementation knows how to put a question to the graph RAG
# service
class KnowledgeQueryImpl:
    def __init__(self, context):
        self.context = context
    async def invoke(self, **arguments):
        client = self.context("graph-rag-request")
        print("Graph RAG question...", flush=True)
        return await client.rag(
            arguments.get("question")
        )

# This tool implementation knows how to do text completion.  This uses
# the prompt service, rather than talking  to TextCompletion directly.
class TextCompletionImpl:
    def __init__(self, context):
        self.context = context
    async def invoke(self, **arguments):
        client = self.context("prompt-request")
        print("Prompt question...", flush=True)
        return await client.question(
            arguments.get("question")
        )

# This tool implementation knows how to do MCP tool invocation.  This uses
# the mcp-tool service.
class McpToolImpl:

    def __init__(self, context, name):
        self.context = context
        self.name = name

    async def invoke(self, **arguments):

        client = self.context("mcp-tool-request")

        print(f"MCP tool invocation: {self.name}...", flush=True)
        output = await client.invoke(
            name = self.name,
            parameters = {},
        )

        print(output)

        if isinstance(output, str):
            return output
        else:
            return json.dumps(output)

        
