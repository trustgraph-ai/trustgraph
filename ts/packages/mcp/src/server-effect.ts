import {OpenAiClient, OpenAiLanguageModel} from "@effect/ai-openai";
import {BunHttpServer, BunRuntime} from "@effect/platform-bun";
import {createTrustGraphSocket, type BaseApi, type Term as ClientTerm} from "@trustgraph/client";
import {Context, Effect, Layer, Redacted} from "effect";
import {LanguageModel, McpServer, Prompt, Tool, Toolkit} from "effect/unstable/ai";
import {FetchHttpClient, HttpRouter} from "effect/unstable/http";
import {HttpApi, HttpApiBuilder, HttpApiEndpoint, HttpApiGroup, HttpApiSchema, OpenApi} from "effect/unstable/httpapi";
import * as S from "effect/Schema";

const annotateTool = <T extends Tool.Any>(
  tool: T,
  annotations: {
    readonly title: string
    readonly readOnly: boolean
    readonly destructive: boolean
    readonly idempotent: boolean
    readonly openWorld: boolean
    readonly strict?: boolean
  },
): T =>
  tool
    .annotate(Tool.Title, annotations.title)
    .annotate(Tool.Readonly, annotations.readOnly)
    .annotate(Tool.Destructive, annotations.destructive)
    .annotate(Tool.Idempotent, annotations.idempotent)
    .annotate(Tool.OpenWorld, annotations.openWorld)
    .annotate(Tool.Strict, annotations.strict ?? true) as T

class PromptSummary extends S.Class<PromptSummary>("PromptSummary")(
  {
    id: S.String.annotateKey({
      description: "Stable prompt template identifier used with get_prompt",
    }),
    name: S.String.annotateKey({
      description: "Human-readable prompt template name",
    }),
  }
) {
}

const IriTerm = S.Struct({
  t: S.Literals(["i"]).annotateKey({
    description: "Term type discriminator for an IRI node",
  }),
  i: S.String.annotateKey({
    description: "IRI value for the graph node or predicate",
  }),
})

const BlankTerm = S.Struct({
  t: S.Literals(["b"]).annotateKey({
    description: "Term type discriminator for a blank node",
  }),
  d: S.String.annotateKey({
    description: "Blank node identifier",
  }),
})

const LiteralTerm = S.Struct({
  t: S.Literals(["l"]).annotateKey({
    description: "Term type discriminator for a literal value",
  }),
  v: S.String.annotateKey({
    description: "Literal lexical value",
  }),
  dt: S.optionalKey(S.String).annotateKey({
    description: "Optional literal datatype IRI",
  }),
  ln: S.optionalKey(S.String).annotateKey({
    description: "Optional literal language tag",
  }),
})

const ReifiedTripleTerm = S.Struct({
  t: S.Literals(["t"]).annotateKey({
    description: "Term type discriminator for a reified triple",
  }),
  tr: S.optionalKey(S.Json).annotateKey({
    description: "Optional embedded triple payload",
  }),
})

const Term = S.Union([IriTerm, BlankTerm, LiteralTerm, ReifiedTripleTerm])

const Triple = S.Struct({
  s: Term.annotateKey({
    description: "Triple subject term",
  }),
  p: Term.annotateKey({
    description: "Triple predicate term",
  }),
  o: Term.annotateKey({
    description: "Triple object term",
  }),
  g: S.optionalKey(S.String).annotateKey({
    description: "Optional named graph or collection identifier",
  }),
})

const ToolTextResult = S.String.annotateKey({
  description: "Human-readable text result returned by the tool",
})

const TrustGraphJsonPayload = S.Json.annotateKey({
  description: "JSON-safe payload returned by the TrustGraph gateway",
})

const ToolErrorCause = S.DefectWithStack.annotateKey({
  description: "Original exception, schema decoding failure, or gateway error that caused the tool call to fail",
})

const ToolErrorMessage = S.String.annotateKey({
  description: "Concise human-readable error message suitable for explaining the failure to a user",
})

export const makeMcpServer = (
  name: string,
  version: string,
) => McpServer.layer(
  {
    version,
    name,
  }
)

export class TextCompletionSuccess extends S.Class<TextCompletionSuccess>("TextCompletionSuccess")(
  {
    text: ToolTextResult,
  }
) {
}

export class TextCompletionError extends S.TaggedErrorClass<TextCompletionError>()(
  "TextCompletionError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class TextCompletionParameters extends S.Class<TextCompletionParameters>("TextCompletionParameters")(
  {
    system: S.String.annotateKey({
      description: "System prompt",
    }),
    prompt: S.String.annotateKey({
      description: "User prompt",
    })
  }
) {
}

export const TextCompletionTool = annotateTool(
  Tool.make("text_completion", {
    description: "Run a text completion using the configured LLM",
    parameters: TextCompletionParameters,
    success: TextCompletionSuccess,
    failure: TextCompletionError,
  }),
  {
    title: "Text Completion",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: true,
  },
)

export class GraphRagSuccess extends S.Class<GraphRagSuccess>("GraphRagSuccess")(
  {
    text: ToolTextResult,
  }
) {
}

export class GraphRagError extends S.TaggedErrorClass<GraphRagError>()(
  "GraphRagError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class GraphRagParameters extends S.Class<GraphRagParameters>("GraphRagParameters")(
  {
    query: S.String.annotateKey({
      description: "Natural language query",
    }),
    entity_limit: S.optionalKey(S.Int).annotateKey({
      description: "Max entities to retrieve"
    }),
    triple_limit: S.optionalKey(S.Int).annotateKey({
      description: "Max triples per entity"
    }),
    collection: S.optionalKey(S.String).annotateKey({
      description: "Collection name"
    })
  }
) {
}

export const GraphRagTool = annotateTool(
  Tool.make("graph_rag", {
    description: "Query the knowledge graph using RAG",
    parameters: GraphRagParameters,
    success: GraphRagSuccess,
    failure: GraphRagError,
  }),
  {
    title: "Graph RAG",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: true,
  },
)

export class DocumentRagSuccess extends S.Class<DocumentRagSuccess>("DocumentRagSuccess")(
  {
    text: ToolTextResult,
  }
) {
}

export class DocumentRagError extends S.TaggedErrorClass<DocumentRagError>()(
  "DocumentRagError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class DocumentRagParameters extends S.Class<DocumentRagParameters>("DocumentRagParameters")(
  {
    query: S.String.annotateKey({
      description: "Natural language query",
    }),
    doc_limit: S.optionalKey(S.Int).annotateKey({
      description: "Max documents to retrieve"
    }),
    collection: S.optionalKey(S.String).annotateKey({
        description: "Collection name"
      }
    )
  }
) {
}

export const DocumentRagTool = annotateTool(
  Tool.make("document_rag", {
    description: "Query documents using RAG",
    parameters: DocumentRagParameters,
    success: DocumentRagSuccess,
    failure: DocumentRagError,
  }),
  {
    title: "Document RAG",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: true,
  },
)

export class AgentSuccess extends S.Class<AgentSuccess>("AgentSuccess")(
  {
    text: ToolTextResult,
  }
) {
}

export class AgentError extends S.TaggedErrorClass<AgentError>()(
  "AgentError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class AgentParameters extends S.Class<AgentParameters>("AgentParameters")(
  {
    question: S.String.annotateKey({
      description: "Question for the agent"
    })
  }
) {
}

export const AgentTool = annotateTool(
  Tool.make("agent", {
    parameters: AgentParameters,
    success: AgentSuccess,
    failure: AgentError,
    description: "Ask the TrustGraph agent a question"
  }),
  {
    title: "TrustGraph Agent",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: true,
  },
)

export class EmbeddingsSuccess extends S.Class<EmbeddingsSuccess>("EmbeddingsSuccess")(
  {
    vectors: S.Finite.pipe(S.Array, S.Array).annotateKey({
      description: "Embedding vectors in the same order as the input texts",
    }),
  }
) {
}

export class EmbeddingsError extends S.TaggedErrorClass<EmbeddingsError>()(
  "EmbeddingsError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class EmbeddingsParameters extends S.Class<EmbeddingsParameters>("EmbeddingsParameters")(
  {
    text: S.Array(S.String).annotateKey({
      description: "Texts to embed"
    })
  }
) {
}

export const EmbeddingsTool = annotateTool(
  Tool.make("embeddings", {
    parameters: EmbeddingsParameters,
    success: EmbeddingsSuccess,
    failure: EmbeddingsError,
    description: "Generate text embeddings"
  }),
  {
    title: "Generate Embeddings",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: true,
  },
)

export class TriplesQuerySuccess extends S.Class<TriplesQuerySuccess>("TriplesQuerySuccess")(
  {
    triples: S.Array(Triple).annotateKey({
      description: "Knowledge graph triples matching the requested subject, predicate, object, collection, and limit filters",
    }),
  }
) {
}

export class TriplesQueryError extends S.TaggedErrorClass<TriplesQueryError>()(
  "TriplesQueryError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class TriplesQueryParameters extends S.Class<TriplesQueryParameters>("TriplesQueryParameters")(
  {
    s: S.optionalKey(S.String).annotateKey({
      description: "Subject IRI"
    }),
    p: S.optionalKey(S.String).annotateKey({
      description: "Predicate IRI"
    }),
    o: S.optionalKey(S.String).annotateKey({
      description: "Object IRI or literal"
    }),
    limit: S.optionalKey(S.Int).annotateKey({
        description: "Max results"
      }
    ),
    collection: S.optionalKey(S.String).annotateKey({
      description: "Collection name"
    })
  }
) {
}

export const TriplesQueryTool = annotateTool(
  Tool.make("triples_query", {
    parameters: TriplesQueryParameters,
    success: TriplesQuerySuccess,
    failure: TriplesQueryError,
    description: "Query the knowledge graph for triples matching a pattern"
  }),
  {
    title: "Triples Query",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: true,
  },
)

export class GraphEmbeddingsQuerySuccess extends S.Class<GraphEmbeddingsQuerySuccess>("GraphEmbeddingsQuerySuccess")(
  {
    entities: S.Array(
      S.Struct({
        entity: S.NullOr(Term).annotateKey({
          description: "Matched graph entity term, or null when the backend could not resolve one",
        }),
        score: S.Finite.annotateKey({
          description: "Similarity score returned by the vector index",
        }),
      })
    ).annotateKey({
      description: "Entities most similar to the query vector, with higher scores indicating stronger similarity",
    }),
  }
) {
}

export class GraphEmbeddingsQueryError extends S.TaggedErrorClass<GraphEmbeddingsQueryError>()(
  "GraphEmbeddingsQueryError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class GraphEmbeddingsQueryParameters extends S.Class<GraphEmbeddingsQueryParameters>("GraphEmbeddingsQueryParameters")(
  {
    query: S.String.annotateKey({
      description: "Text to find similar entities for"
    }),
    limit: S.optionalKey(S.Int).annotateKey({
        description: "Max results"
      }
    ),
    collection: S.optionalKey(S.String).annotateKey({
      description: "Collection name"
    })
  }
) {
}

export const GraphEmbeddingsQueryTool = annotateTool(
  Tool.make("graph_embeddings_query", {
    parameters: GraphEmbeddingsQueryParameters,
    success: GraphEmbeddingsQuerySuccess,
    failure: GraphEmbeddingsQueryError,
    description: "Find entities similar to a text query using vector embeddings"
  }),
  {
    title: "Graph Embeddings Query",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: true,
  },
)

export class GetConfigAllSuccess extends S.Class<GetConfigAllSuccess>("GetConfigAllSuccess")(
  {
    config: TrustGraphJsonPayload,
  }
) {
}

export class GetConfigAllError extends S.TaggedErrorClass<GetConfigAllError>()(
  "GetConfigAllError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class GetConfigAllParameters extends S.Class<GetConfigAllParameters>("GetConfigAllParameters")(
  {}
) {
}

export const GetConfigAllTool = annotateTool(
  Tool.make("get_config_all", {
    parameters: GetConfigAllParameters,
    success: GetConfigAllSuccess,
    failure: GetConfigAllError,
    description: "Get all configuration values"
  }),
  {
    title: "Get All Config",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: false,
  },
)


export class GetConfigSuccess extends S.Class<GetConfigSuccess>("GetConfigSuccess")(
  {
    config: TrustGraphJsonPayload,
  }
) {
}

export class GetConfigError extends S.TaggedErrorClass<GetConfigError>()(
  "GetConfigError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class GetConfigParameters extends S.Class<GetConfigParameters>("GetConfigParameters")(
  {
    keys: S.Array(
      S.Struct({
        type: S.String.annotateKey({
          description: "Config type"
        }),
        key: S.String.annotateKey({
          description: "Config key"
        })
      })
    ).annotateKey({
      description: "Config keys to retrieve"
    })
  }
) {
}

export const GetConfigTool = annotateTool(
  Tool.make("get_config", {
    parameters: GetConfigParameters,
    success: GetConfigSuccess,
    failure: GetConfigError,
    description: "Get specific configuration values"
  }),
  {
    title: "Get Config",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: false,
  },
)

export class PutConfigSuccess extends S.Class<PutConfigSuccess>("PutConfigSuccess")(
  {
    response: TrustGraphJsonPayload,
  }
) {
}

export class PutConfigError extends S.TaggedErrorClass<PutConfigError>()(
  "PutConfigError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class PutConfigParameters extends S.Class<PutConfigParameters>("PutConfigParameters")(
  {
    values: S.Array(
      S.Struct({
        type: S.String.annotateKey({
          description: "Config type"
        }),
        key: S.String.annotateKey({
          description: "Config key"
        }),
        value: S.String.annotateKey({
          description: "Config values (JSON-encoded)"
        })
      })
    ).annotateKey({
      description: "Key-value entries to set"
    })
  }
) {
}

export const PutConfigTool = annotateTool(
  Tool.make("put_config", {
    parameters: PutConfigParameters,
    success: PutConfigSuccess,
    failure: PutConfigError,
    description: "Set configuration values"
  }),
  {
    title: "Put Config",
    readOnly: false,
    destructive: true,
    idempotent: true,
    openWorld: false,
  },
)

export class DeleteConfigSuccess extends S.Class<DeleteConfigSuccess>("DeleteConfigSuccess")(
  {
    response: TrustGraphJsonPayload,
  }
) {
}

export class DeleteConfigError extends S.TaggedErrorClass<DeleteConfigError>()(
  "DeleteConfigError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class DeleteConfigParameters extends S.Class<DeleteConfigParameters>("DeleteConfigParameters")(
  {
    type: S.String.annotateKey({
      description: "Config type"
    }),
    key: S.String.annotateKey({
      description: "Config key"
    }),
  }
) {
}

export const DeleteConfigTool = annotateTool(
  Tool.make("delete_config", {
    parameters: DeleteConfigParameters,
    success: DeleteConfigSuccess,
    failure: DeleteConfigError,
    description: "Delete a configuration entry"
  }),
  {
    title: "Delete Config",
    readOnly: false,
    destructive: true,
    idempotent: true,
    openWorld: false,
  },
)

export class GetFlowSuccess extends S.Class<GetFlowSuccess>("GetFlowSuccess")(
  {
    flow: TrustGraphJsonPayload,
  }
) {
}

export class GetFlowError extends S.TaggedErrorClass<GetFlowError>()(
  "GetFlowError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class GetFlowParameters extends S.Class<GetFlowParameters>("GetFlowParameters")(
  {
   flow_id: S.String.annotateKey({
     description: "Flow ID to retrieve"
   })
  }
) {
}

export const GetFlowTool = annotateTool(
  Tool.make("get_flow", {
    parameters: GetFlowParameters,
    success: GetFlowSuccess,
    failure: GetFlowError,
    description: "Get a specific flow definition"
  }),
  {
    title: "Get Flow",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: false,
  },
)

export class GetFlowsSuccess extends S.Class<GetFlowsSuccess>("GetFlowsSuccess")(
  {
    flow_ids: S.Array(S.String).annotateKey({
      description: "Available TrustGraph flow identifiers",
    }),
  }
) {
}

export class GetFlowsError extends S.TaggedErrorClass<GetFlowsError>()(
  "GetFlowsError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class GetFlowsParameters extends S.Class<GetFlowsParameters>("GetFlowsParameters")(
  {}
) {
}

export const GetFlowsTool = annotateTool(
  Tool.make("get_flows", {
    parameters: GetFlowsParameters,
    success: GetFlowsSuccess,
    failure: GetFlowsError,
    description: "List all available flows"
  }),
  {
    title: "Get Flows",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: false,
  },
)

export class StartFlowSuccess extends S.Class<StartFlowSuccess>("StartFlowSuccess")(
  {
    response: TrustGraphJsonPayload,
  }
) {
}

export class StartFlowError extends S.TaggedErrorClass<StartFlowError>()(
  "StartFlowError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class StartFlowParameters extends S.Class<StartFlowParameters>("StartFlowParameters")(
  {
    flow_id: S.String.annotateKey({
      description: "Flow ID"
    }),
    blueprint_name: S.String.annotateKey({
      description: "Blueprint name"
    }),
    description: S.String.annotateKey({
      description: "Flow description"
    }),
    parameters: S.optionalKey(S.Record(S.String, S.Unknown)).annotateKey({
      description: "Optional flow parameters"
    })
  }
) {
}

export const StartFlowTool = annotateTool(
  Tool.make("start_flow", {
    parameters: StartFlowParameters,
    success: StartFlowSuccess,
    failure: StartFlowError,
    description: "Start a flow instance"
  }),
  {
    title: "Start Flow",
    readOnly: false,
    destructive: false,
    idempotent: false,
    openWorld: true,
  },
)

export class StopFlowSuccess extends S.Class<StopFlowSuccess>("StopFlowSuccess")(
  {
    response: TrustGraphJsonPayload,
  }
) {
}

export class StopFlowError extends S.TaggedErrorClass<StopFlowError>()(
  "StopFlowError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class StopFlowParameters extends S.Class<StopFlowParameters>("StopFlowParameters")(
  {
    flow_id: S.String.annotateKey({
      description: "Flow ID to stop"
    })
  }
) {
}

export const StopFlowTool = annotateTool(
  Tool.make("stop_flow", {
    parameters: StopFlowParameters,
    success: StopFlowSuccess,
    failure: StopFlowError,
    description: "Stop a running flow"
  }),
  {
    title: "Stop Flow",
    readOnly: false,
    destructive: true,
    idempotent: true,
    openWorld: false,
  },
)

export class GetDocumentsSuccess extends S.Class<GetDocumentsSuccess>("GetDocumentsSuccess")(
  {
    documents: S.Array(S.Json).annotateKey({
      description: "Document metadata records currently registered in the TrustGraph library",
    }),
  }
) {
}

export class GetDocumentsError extends S.TaggedErrorClass<GetDocumentsError>()(
  "GetDocumentsError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class GetDocumentsParameters extends S.Class<GetDocumentsParameters>("GetDocumentsParameters")(
  {}
) {
}

export const GetDocumentsTool = annotateTool(
  Tool.make("get_documents", {
    parameters: GetDocumentsParameters,
    success: GetDocumentsSuccess,
    failure: GetDocumentsError,
    description: "List all documents in the library"
  }),
  {
    title: "Get Documents",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: true,
  },
)

export class LoadDocumentSuccess extends S.Class<LoadDocumentSuccess>("LoadDocumentSuccess")(
  {
    response: TrustGraphJsonPayload,
  }
) {
}

export class LoadDocumentError extends S.TaggedErrorClass<LoadDocumentError>()(
  "LoadDocumentError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class LoadDocumentParameters extends S.Class<LoadDocumentParameters>("LoadDocumentParameters")(
  {
    document: S.String.annotateKey({
      description: "Base64-encoded document content"
    }),
    mime_type: S.String.annotateKey({
      description: "Document MIME type"
    }),
    title: S.String.annotateKey({
      description: "Document title"
    }),
    comments: S.optionalKey(S.String).annotateKey({
      description: "Additional comments"
    }),
    tags: S.String.pipe(S.Array, S.optionalKey).annotateKey({
      description: "Document tags"
    }),
    id: S.optionalKey(S.String).annotateKey({
      description: "Optional document ID"
    })
  }
) {
}

export const LoadDocumentTool = annotateTool(
  Tool.make("load_document", {
    parameters: LoadDocumentParameters,
    success: LoadDocumentSuccess,
    failure: LoadDocumentError,
    description: "Upload a document to the library"
  }),
  {
    title: "Load Document",
    readOnly: false,
    destructive: false,
    idempotent: false,
    openWorld: false,
  },
)

export class RemoveDocumentSuccess extends S.Class<RemoveDocumentSuccess>("RemoveDocumentSuccess")(
  {
    response: TrustGraphJsonPayload,
  }
) {
}

export class RemoveDocumentError extends S.TaggedErrorClass<RemoveDocumentError>()(
  "RemoveDocumentError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class RemoveDocumentParameters extends S.Class<RemoveDocumentParameters>("RemoveDocumentParameters")(
  {
    id: S.String.annotateKey({
      description: "Document ID to remove"
    }),
    collection: S.optionalKey(S.String).annotateKey({
      description: "Collection name"
    })
  }
) {
}

export const RemoveDocumentTool = annotateTool(
  Tool.make("remove_document", {
    parameters: RemoveDocumentParameters,
    success: RemoveDocumentSuccess,
    failure: RemoveDocumentError,
    description: "Remove a document from the library"
  }),
  {
    title: "Remove Document",
    readOnly: false,
    destructive: true,
    idempotent: true,
    openWorld: false,
  },
)

export class GetPromptsSuccess extends S.Class<GetPromptsSuccess>("GetPromptsSuccess")(
  {
    prompts: S.Array(PromptSummary).annotateKey({
      description: "Prompt templates available for retrieval with get_prompt",
    }),
  }
) {
}

export class GetPromptsError extends S.TaggedErrorClass<GetPromptsError>()(
  "GetPromptsError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class GetPromptsParameters extends S.Class<GetPromptsParameters>("GetPromptsParameters")(
  {}
) {
}

export const GetPromptsTool = annotateTool(
  Tool.make("get_prompts", {
    parameters: GetPromptsParameters,
    success: GetPromptsSuccess,
    failure: GetPromptsError,
    description: "List available prompt templates"
  }),
  {
    title: "Get Prompts",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: false,
  },
)

export class GetPromptSuccess extends S.Class<GetPromptSuccess>("GetPromptSuccess")(
  {
    prompt: TrustGraphJsonPayload,
  }
) {
}

export class GetPromptError extends S.TaggedErrorClass<GetPromptError>()(
  "GetPromptError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class GetPromptParameters extends S.Class<GetPromptParameters>("GetPromptParameters")(
  {
    id: S.String.annotateKey({
      description: "Prompt template ID"
    })
  }
) {
}

export const GetPromptTool = annotateTool(
  Tool.make("get_prompt", {
    parameters: GetPromptParameters,
    success: GetPromptSuccess,
    failure: GetPromptError,
    description: "Get a specific prompt template"
  }),
  {
    title: "Get Prompt",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: false,
  },
)

export class GetKnowledgeCoresSuccess extends S.Class<GetKnowledgeCoresSuccess>("GetKnowledgeCoresSuccess")(
  {
    ids: S.Array(S.String).annotateKey({
      description: "Available knowledge graph core identifiers",
    }),
  }
) {
}

export class GetKnowledgeCoresError extends S.TaggedErrorClass<GetKnowledgeCoresError>()(
  "GetKnowledgeCoresError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class GetKnowledgeCoresParameters extends S.Class<GetKnowledgeCoresParameters>("GetKnowledgeCoresParameters")(
  {}
) {
}

export const GetKnowledgeCoresTool = annotateTool(
  Tool.make("get_knowledge_cores", {
    parameters: GetKnowledgeCoresParameters,
    success: GetKnowledgeCoresSuccess,
    failure: GetKnowledgeCoresError,
    description: "List available knowledge graph cores"
  }),
  {
    title: "Get Knowledge Cores",
    readOnly: true,
    destructive: false,
    idempotent: false,
    openWorld: false,
  },
)

export class DeleteKgCoreSuccess extends S.Class<DeleteKgCoreSuccess>("DeleteKgCoreSuccess")(
  {
    response: TrustGraphJsonPayload,
  }
) {
}

export class DeleteKgCoreError extends S.TaggedErrorClass<DeleteKgCoreError>()(
  "DeleteKgCoreError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class DeleteKgCoreParameters extends S.Class<DeleteKgCoreParameters>("DeleteKgCoreParameters")(
  {
    id: S.String.annotateKey({
      description: "Knowledge core ID"
    }),
    collection: S.optionalKey(S.String).annotateKey({
      description: "Collection name"
    })
  }
) {
}

export const DeleteKgCoreTool = annotateTool(
  Tool.make("delete_kg_core", {
    parameters: DeleteKgCoreParameters,
    success: DeleteKgCoreSuccess,
    failure: DeleteKgCoreError,
    description: "Delete a knowledge graph core"
  }),
  {
    title: "Delete KG Core",
    readOnly: false,
    destructive: true,
    idempotent: true,
    openWorld: false,
  },
)

export class LoadKgCoreSuccess extends S.Class<LoadKgCoreSuccess>("LoadKgCoreSuccess")(
  {
    response: TrustGraphJsonPayload,
  }
) {
}

export class LoadKgCoreError extends S.TaggedErrorClass<LoadKgCoreError>()(
  "LoadKgCoreError",
  {
    cause: ToolErrorCause,
    message: ToolErrorMessage,
  }
) {
}

export class LoadKgCoreParameters extends S.Class<LoadKgCoreParameters>("LoadKgCoreParameters")(
  {
    id: S.String.annotateKey({
      description: "Knowledge core ID"
    }),
    flow: S.String.annotateKey({
      description: "Flow to use for loading"
    }),
    collection: S.optionalKey(S.String).annotateKey({
      description: "Collection name"
    })
  }
) {
}

export const LoadKgCoreTool = annotateTool(
  Tool.make("load_kg_core", {
    parameters: LoadKgCoreParameters,
    success: LoadKgCoreSuccess,
    failure: LoadKgCoreError,
    description: "Load a knowledge graph core"
  }),
  {
    title: "Load KG Core",
    readOnly: false,
    destructive: false,
    idempotent: false,
    openWorld: false,
  },
)

export const TrustGraphMcpToolkit = Toolkit.make(
  TextCompletionTool,
  GraphRagTool,
  DocumentRagTool,
  AgentTool,
  EmbeddingsTool,
  TriplesQueryTool,
  GraphEmbeddingsQueryTool,
  GetConfigAllTool,
  GetConfigTool,
  PutConfigTool,
  DeleteConfigTool,
  GetFlowsTool,
  GetFlowTool,
  StartFlowTool,
  StopFlowTool,
  GetDocumentsTool,
  LoadDocumentTool,
  RemoveDocumentTool,
  GetPromptsTool,
  GetPromptTool,
  GetKnowledgeCoresTool,
  DeleteKgCoreTool,
  LoadKgCoreTool,
)

export interface TrustGraphMcpOptions {
  readonly gatewayUrl?: string | undefined
  readonly user?: string | undefined
  readonly token?: string | undefined
  readonly flowId?: string | undefined
  readonly name?: string | undefined
  readonly version?: string | undefined
  readonly mcpPath?: HttpRouter.PathInput | undefined
  readonly openAiModel?: string | undefined
  readonly openAiApiKey?: string | undefined
  readonly port?: number | undefined
}

export interface TrustGraphMcpConfigShape {
  readonly gatewayUrl: string
  readonly user: string
  readonly token: string | undefined
  readonly flowId: string
  readonly name: string
  readonly version: string
  readonly mcpPath: HttpRouter.PathInput
  readonly openAiModel: string
  readonly openAiApiKey: string | undefined
  readonly port: number
}

const readNonEmpty = (value: string | undefined): string | undefined =>
  value !== undefined && value.length > 0 ? value : undefined

const resolvePort = (value: number | undefined): number => {
  if (value !== undefined) {
    return value
  }
  const raw = readNonEmpty(process.env.PORT)
  if (raw === undefined) {
    return 3000
  }
  const parsed = Number.parseInt(raw, 10)
  return Number.isFinite(parsed) ? parsed : 3000
}

export const resolveTrustGraphMcpConfig = (
  options: TrustGraphMcpOptions = {},
): TrustGraphMcpConfigShape => ({
  gatewayUrl: options.gatewayUrl ?? process.env.GATEWAY_URL ?? "ws://localhost:8088/api/v1/rpc",
  user: options.user ?? process.env.USER_ID ?? "mcp",
  token: options.token ?? readNonEmpty(process.env.GATEWAY_SECRET),
  flowId: options.flowId ?? process.env.FLOW_ID ?? "default",
  name: options.name ?? "trustgraph",
  version: options.version ?? "0.1.0",
  mcpPath: options.mcpPath ?? "/mcp",
  openAiModel: options.openAiModel ?? process.env.OPENAI_MODEL ?? "gpt-4.1",
  openAiApiKey: options.openAiApiKey ?? readNonEmpty(process.env.OPENAI_API_KEY) ?? readNonEmpty(process.env.OPENAI_TOKEN),
  port: resolvePort(options.port),
})

export class TrustGraphMcpConfig extends Context.Service<TrustGraphMcpConfig, TrustGraphMcpConfigShape>()(
  "@trustgraph/mcp/server-effect/TrustGraphMcpConfig",
) {
  static readonly layer = (options: TrustGraphMcpOptions = {}) =>
    Layer.succeed(
      TrustGraphMcpConfig,
      TrustGraphMcpConfig.of(resolveTrustGraphMcpConfig(options)),
    )
}

export class TrustGraphSocket extends Context.Service<TrustGraphSocket, BaseApi>()(
  "@trustgraph/mcp/server-effect/TrustGraphSocket",
) {
  static readonly layer = Layer.effect(
    TrustGraphSocket,
    Effect.gen(function*() {
      const config = yield* TrustGraphMcpConfig
      const socket = yield* Effect.acquireRelease(
        Effect.sync(() => createTrustGraphSocket(config.user, config.token, config.gatewayUrl)),
        (socket) => Effect.sync(() => socket.close()),
      )
      return TrustGraphSocket.of(socket)
    }),
  )
}

const toErrorMessage = (cause: unknown): string => {
  if (cause instanceof Error && cause.message.length > 0) {
    return cause.message
  }
  if (typeof cause === "string" && cause.length > 0) {
    return cause
  }
  if (cause !== null && typeof cause === "object" && "message" in cause) {
    const message = (cause as { readonly message?: unknown }).message
    if (typeof message === "string" && message.length > 0) {
      return message
    }
  }
  return "TrustGraph MCP tool failed"
}

const decodeJson = S.decodeUnknownEffect(S.Json)
const decodeJsonArray = S.decodeUnknownEffect(S.Array(S.Json))

const decodeJsonOrFail = <E>(
  value: unknown,
  makeError: (cause: unknown) => E,
) => decodeJson(value).pipe(
  Effect.mapError(makeError),
)

const decodeJsonArrayOrFail = <E>(
  value: unknown,
  makeError: (cause: unknown) => E,
) => decodeJsonArray(value).pipe(
  Effect.mapError(makeError),
)

const asIriTerm = (value: string | undefined): ClientTerm | undefined =>
  value !== undefined && value.length > 0 ? {t: "i", i: value} : undefined

const openAiApiKeyOptions = (apiKey: string | undefined) =>
  apiKey === undefined
    ? {}
    : {apiKey: Redacted.make(apiKey)}

export const makeOpenAiProviderLayer = (
  options: TrustGraphMcpOptions = {},
) => {
  const config = resolveTrustGraphMcpConfig(options)
  return OpenAiLanguageModel.layer({
    model: config.openAiModel,
    config: {
      strictJsonSchema: true,
    },
  }).pipe(
    Layer.provide(OpenAiClient.layer(openAiApiKeyOptions(config.openAiApiKey))),
    Layer.provide(FetchHttpClient.layer),
  )
}

export const TrustGraphMcpToolkitLive = TrustGraphMcpToolkit.toLayer(
  Effect.gen(function*() {
    const config = yield* TrustGraphMcpConfig
    const socket = yield* TrustGraphSocket
    const model = yield* LanguageModel.LanguageModel

    return TrustGraphMcpToolkit.of({
      text_completion: Effect.fn("TrustGraphMcp.text_completion")(function*({system, prompt}) {
        const response = yield* model.generateText({
          prompt: Prompt.make(prompt).pipe(Prompt.setSystem(system)),
        })
        return new TextCompletionSuccess({text: response.text})
      }),

      graph_rag: ({query, entity_limit, triple_limit, collection}) =>
        Effect.tryPromise({
          try: async () => {
            const response = await socket.flow(config.flowId).graphRag(
              query,
              {
                ...(entity_limit !== undefined ? {entityLimit: entity_limit} : {}),
                ...(triple_limit !== undefined ? {tripleLimit: triple_limit} : {}),
              },
              collection,
            )
            return new GraphRagSuccess({text: response})
          },
          catch: (cause) => new GraphRagError({cause, message: toErrorMessage(cause)}),
        }),

      document_rag: ({query, doc_limit, collection}) =>
        Effect.tryPromise({
          try: async () => {
            const response = await socket.flow(config.flowId).documentRag(query, doc_limit, collection)
            return new DocumentRagSuccess({text: response})
          },
          catch: (cause) => new DocumentRagError({cause, message: toErrorMessage(cause)}),
        }),

      agent: ({question}) =>
        Effect.callback<AgentSuccess, AgentError>((resume) => {
          let fullAnswer = ""
          socket.flow(config.flowId).agent(
            question,
            () => {},
            () => {},
            (chunk, complete) => {
              fullAnswer += chunk
              if (complete) {
                resume(Effect.succeed(new AgentSuccess({text: fullAnswer})))
              }
            },
            (cause) => resume(Effect.fail(new AgentError({cause, message: toErrorMessage(cause)}))),
          )
        }),

      embeddings: ({text}) =>
        Effect.tryPromise({
          try: async () => {
            const vectors = await socket.flow(config.flowId).embeddings([...text])
            return new EmbeddingsSuccess({vectors})
          },
          catch: (cause) => new EmbeddingsError({cause, message: toErrorMessage(cause)}),
        }),

      triples_query: ({s, p, o, limit, collection}) =>
        Effect.tryPromise({
          try: async () => {
            const triples = await socket.flow(config.flowId).triplesQuery(
              asIriTerm(s),
              asIriTerm(p),
              asIriTerm(o),
              limit,
              collection,
            )
            return new TriplesQuerySuccess({triples})
          },
          catch: (cause) => new TriplesQueryError({cause, message: toErrorMessage(cause)}),
        }),

      graph_embeddings_query: ({query, limit, collection}) =>
        Effect.tryPromise({
          try: async () => {
            const vectors = await socket.flow(config.flowId).embeddings([query])
            const entities = await socket.flow(config.flowId).graphEmbeddingsQuery(
              vectors[0] ?? [],
              limit ?? 10,
              collection,
            )
            return new GraphEmbeddingsQuerySuccess({entities})
          },
          catch: (cause) => new GraphEmbeddingsQueryError({cause, message: toErrorMessage(cause)}),
        }),

      get_config_all: () =>
        Effect.tryPromise({
          try: () => socket.config().getConfigAll(),
          catch: (cause) => new GetConfigAllError({cause, message: toErrorMessage(cause)}),
        }).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => new GetConfigAllError({cause, message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((config) => new GetConfigAllSuccess({config})),
            )
          ),
        ),

      get_config: ({keys}) =>
        Effect.tryPromise({
          try: () => socket.config().getConfig(keys.map(({type, key}) => ({type, key}))),
          catch: (cause) => new GetConfigError({cause, message: toErrorMessage(cause)}),
        }).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => new GetConfigError({cause, message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((config) => new GetConfigSuccess({config})),
            )
          ),
        ),

      put_config: ({values}) =>
        Effect.tryPromise({
          try: () => socket.config().putConfig(values.map(({type, key, value}) => ({type, key, value}))),
          catch: (cause) => new PutConfigError({cause, message: toErrorMessage(cause)}),
        }).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => new PutConfigError({cause, message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => new PutConfigSuccess({response})),
            )
          ),
        ),

      delete_config: ({type, key}) =>
        Effect.tryPromise({
          try: () => socket.config().deleteConfig({type, key}),
          catch: (cause) => new DeleteConfigError({cause, message: toErrorMessage(cause)}),
        }).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => new DeleteConfigError({cause, message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => new DeleteConfigSuccess({response})),
            )
          ),
        ),

      get_flows: () =>
        Effect.tryPromise({
          try: async () => new GetFlowsSuccess({flow_ids: await socket.flows().getFlows()}),
          catch: (cause) => new GetFlowsError({cause, message: toErrorMessage(cause)}),
        }),

      get_flow: ({flow_id}) =>
        Effect.tryPromise({
          try: () => socket.flows().getFlow(flow_id),
          catch: (cause) => new GetFlowError({cause, message: toErrorMessage(cause)}),
        }).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => new GetFlowError({cause, message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((flow) => new GetFlowSuccess({flow})),
            )
          ),
        ),

      start_flow: ({flow_id, blueprint_name, description, parameters}) =>
        Effect.tryPromise({
          try: async () =>
            socket.flows().startFlow(
              flow_id,
              blueprint_name,
              description,
              parameters === undefined ? undefined : {...parameters},
            ),
          catch: (cause) => new StartFlowError({cause, message: toErrorMessage(cause)}),
        }).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => new StartFlowError({cause, message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => new StartFlowSuccess({response})),
            )
          ),
        ),

      stop_flow: ({flow_id}) =>
        Effect.tryPromise({
          try: () => socket.flows().stopFlow(flow_id),
          catch: (cause) => new StopFlowError({cause, message: toErrorMessage(cause)}),
        }).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => new StopFlowError({cause, message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => new StopFlowSuccess({response})),
            )
          ),
        ),

      get_documents: () =>
        Effect.tryPromise({
          try: () => socket.librarian().getDocuments(),
          catch: (cause) => new GetDocumentsError({cause, message: toErrorMessage(cause)}),
        }).pipe(
          Effect.flatMap((value) =>
            decodeJsonArrayOrFail(
              value,
              (cause) => new GetDocumentsError({cause, message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((documents) => new GetDocumentsSuccess({documents})),
            )
          ),
        ),

      load_document: ({document, mime_type, title, comments, tags, id}) =>
        Effect.tryPromise({
          try: async () =>
            socket.librarian().loadDocument(
              document,
              mime_type,
              title,
              comments ?? "",
              tags === undefined ? [] : [...tags],
              id,
            ),
          catch: (cause) => new LoadDocumentError({cause, message: toErrorMessage(cause)}),
        }).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => new LoadDocumentError({cause, message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => new LoadDocumentSuccess({response})),
            )
          ),
        ),

      remove_document: ({id, collection}) =>
        Effect.tryPromise({
          try: () => socket.librarian().removeDocument(id, collection),
          catch: (cause) => new RemoveDocumentError({cause, message: toErrorMessage(cause)}),
        }).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => new RemoveDocumentError({cause, message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => new RemoveDocumentSuccess({response})),
            )
          ),
        ),

      get_prompts: () =>
        Effect.tryPromise({
          try: async () => new GetPromptsSuccess({prompts: await socket.config().getPrompts()}),
          catch: (cause) => new GetPromptsError({cause, message: toErrorMessage(cause)}),
        }),

      get_prompt: ({id}) =>
        Effect.tryPromise({
          try: () => socket.config().getPrompt(id),
          catch: (cause) => new GetPromptError({cause, message: toErrorMessage(cause)}),
        }).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => new GetPromptError({cause, message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((prompt) => new GetPromptSuccess({prompt})),
            )
          ),
        ),

      get_knowledge_cores: () =>
        Effect.tryPromise({
          try: async () => new GetKnowledgeCoresSuccess({ids: await socket.knowledge().getKnowledgeCores()}),
          catch: (cause) => new GetKnowledgeCoresError({cause, message: toErrorMessage(cause)}),
        }),

      delete_kg_core: ({id, collection}) =>
        Effect.tryPromise({
          try: () => socket.knowledge().deleteKgCore(id, collection),
          catch: (cause) => new DeleteKgCoreError({cause, message: toErrorMessage(cause)}),
        }).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => new DeleteKgCoreError({cause, message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => new DeleteKgCoreSuccess({response})),
            )
          ),
        ),

      load_kg_core: ({id, flow, collection}) =>
        Effect.tryPromise({
          try: () => socket.knowledge().loadKgCore(id, flow, collection),
          catch: (cause) => new LoadKgCoreError({cause, message: toErrorMessage(cause)}),
        }).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => new LoadKgCoreError({cause, message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => new LoadKgCoreSuccess({response})),
            )
          ),
        ),
    })
  }),
)

export class TrustGraphMcpHttpApi extends HttpApi.make("trustgraph-mcp")
  .add(
    HttpApiGroup.make("mcp", {topLevel: true}).add(
      HttpApiEndpoint.get("mcpHealth", "/mcp/health", {
        success: HttpApiSchema.NoContent,
      }),
    ),
  )
  .annotateMerge(
    OpenApi.annotations({
      title: "TrustGraph MCP API",
    }),
  )
{}

export const TrustGraphMcpHttpApiHandlers = HttpApiBuilder.group(
  TrustGraphMcpHttpApi,
  "mcp",
  Effect.fn(function*(handlers) {
    return handlers.handle("mcpHealth", () => Effect.void)
  }),
)

export const TrustGraphMcpHttpApiRoutes = HttpApiBuilder.layer(
  TrustGraphMcpHttpApi,
  {
    openapiPath: "/mcp/openapi.json",
  },
).pipe(
  Layer.provide(TrustGraphMcpHttpApiHandlers),
)

export const makeTrustGraphMcpHttpLayer = (
  options: TrustGraphMcpOptions = {},
) => {
  const config = resolveTrustGraphMcpConfig(options)
  const tools = McpServer.toolkit(TrustGraphMcpToolkit).pipe(
    Layer.provide(TrustGraphMcpToolkitLive),
    Layer.provide(makeOpenAiProviderLayer(config)),
  )

  return Layer.mergeAll(
    TrustGraphMcpHttpApiRoutes,
    tools,
  ).pipe(
    Layer.provide(McpServer.layerHttp({
      name: config.name,
      version: config.version,
      path: config.mcpPath,
    })),
    Layer.provide(TrustGraphSocket.layer),
    Layer.provide(TrustGraphMcpConfig.layer(config)),
  )
}

export const makeTrustGraphMcpHttpServerLayer = (
  options: TrustGraphMcpOptions = {},
) => {
  const config = resolveTrustGraphMcpConfig(options)
  return HttpRouter.serve(makeTrustGraphMcpHttpLayer(config)).pipe(
    Layer.provide(BunHttpServer.layer({port: config.port})),
  )
}

export const runHttp = (options: TrustGraphMcpOptions = {}): void => {
  Layer.launch(makeTrustGraphMcpHttpServerLayer(options)).pipe(BunRuntime.runMain)
}
