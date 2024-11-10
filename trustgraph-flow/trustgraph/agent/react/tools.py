
# from . types import Tool

# class CatsKb:
#     tool = Tool(
#         name = "cats-kb",
#         description = "Query a knowledge base with information about Mark's cats.  The query should be a simple natural language question",
#         arguments = [
#             Argument(
#                 name = "query",
#                 type = "string",
#                 description = "The search query string"
#             )
#         ]
#     )
#     def __init__(self, context):
#         self.context = context
#     def invoke(self, **arguments):
#         return self.context.graph_rag.request(arguments.get("query"))

# class ShuttleKb:
#     tool = Tool(
#         name = "shuttle-kb",
#         description = "Query a knowledge base with information about the space shuttle.  The query should be a simple natural language question",
#         arguments = [
#             Argument(
#                 name = "query",
#                 type = "string",
#                 description = "The search query string"
#             )
#         ]
#     )
#     def __init__(self, context):
#         self.context = context
#     def invoke(self, **arguments):
#         return self.context.graph_rag.request(arguments.get("query"))

# class Compute:
#     tool = Tool(
#         name = "compute",
#         description = "A computation engine which can answer questions about maths and computation",
#         arguments = [
#             Argument(
#                 name = "computation",
#                 type = "string",
#                 description = "The computation to solve"
#             )
#         ]
#     )
#     def __init__(self, context):
#         self.context = context
#     def invoke(self, **arguments):
#         return self.context.prompt.request(
#             "question", { "question": arguments.get("computation") }
#         )


class KnowledgeQueryImpl:
    def __init__(self, context):
        self.context = context
    def invoke(self, **arguments):
        return self.context.graph_rag.request(arguments.get("query"))

class TextCompletionImpl:
    def __init__(self, context):
        self.context = context
    def invoke(self, **arguments):
        return self.context.prompt.request(
            "question", { "question": arguments.get("computation") }
        )

