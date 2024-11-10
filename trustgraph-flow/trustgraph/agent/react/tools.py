
# This tool implementation knows how to put a question to the graph RAG
# service
class KnowledgeQueryImpl:
    def __init__(self, context):
        self.context = context
    def invoke(self, **arguments):
        return self.context.graph_rag.request(arguments.get("query"))

# This tool implementation knows how to do text completion.  This uses
# the prompt service, rather than talking  to TextCompletion directly.
class TextCompletionImpl:
    def __init__(self, context):
        self.context = context
    def invoke(self, **arguments):
        return self.context.prompt.request(
            "question", { "question": arguments.get("computation") }
        )

