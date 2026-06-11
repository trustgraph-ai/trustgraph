import {BunHttpServer, BunRuntime} from "@effect/platform-bun";
import {NodeRuntime, NodeStdio} from "@effect/platform-node";
import type {
  EntityMatch as ClientEntityMatch,
  Term as ClientTerm,
  Triple as ClientTriple,
  TrustGraphGatewayClient,
} from "@trustgraph/client";
import {
  makeTrustGraphGatewayClientScoped,
} from "@trustgraph/client";
import {Clock, Config, Context, Effect, Layer} from "effect";
import * as O from "effect/Option";
import * as Predicate from "effect/Predicate";
import {McpServer, Tool, Toolkit} from "effect/unstable/ai";
import {HttpRouter} from "effect/unstable/http";
import {HttpApi, HttpApiBuilder, HttpApiEndpoint, HttpApiGroup, HttpApiSchema, OpenApi} from "effect/unstable/httpapi";
import * as S from "effect/Schema";

const annotateTool = <Name extends string, Config extends {
  readonly parameters: S.Top
  readonly success: S.Top
  readonly failure: S.Top
  readonly failureMode: Tool.FailureMode
}, Requirements>(
  tool: Tool.Tool<Name, Config, Requirements>,
  annotations: {
    readonly title: string
    readonly readOnly: boolean
    readonly destructive: boolean
    readonly idempotent: boolean
    readonly openWorld: boolean
    readonly strict?: boolean
  },
): Tool.Tool<Name, Config, Requirements> =>
  tool
    .annotate(Tool.Title, annotations.title)
    .annotate(Tool.Readonly, annotations.readOnly)
    .annotate(Tool.Destructive, annotations.destructive)
    .annotate(Tool.Idempotent, annotations.idempotent)
    .annotate(Tool.OpenWorld, annotations.openWorld)
    .annotate(Tool.Strict, annotations.strict ?? true)

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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
    failureMode: "error",
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
  readonly port?: number | undefined
}

const McpPathInput = S.Union([S.Literal("*"), S.TemplateLiteral(["/", S.String])])

export class TrustGraphMcpConfigShape extends S.Class<TrustGraphMcpConfigShape>("TrustGraphMcpConfigShape")({
  gatewayUrl: S.String,
  user: S.String,
  token: S.UndefinedOr(S.String),
  flowId: S.String,
  name: S.String,
  version: S.String,
  mcpPath: McpPathInput,
  port: S.Finite,
}, { description: "Resolved TrustGraph MCP server configuration." }) {}

const readNonEmpty = (value: string | undefined): string | undefined =>
  value !== undefined && value.length > 0 ? value : undefined

const gatewayUrlWithToken = (config: TrustGraphMcpConfigShape): string => {
  if (config.token === undefined || config.token.length === 0) return config.gatewayUrl
  const separator = config.gatewayUrl.includes("?") ? "&" : "?"
  return `${config.gatewayUrl}${separator}token=${encodeURIComponent(config.token)}`
}

const parsePort = (raw: string | undefined): number => {
  if (raw === undefined) {
    return 3000
  }
  const parsed = Number.parseInt(raw, 10)
  return Number.isFinite(parsed) ? parsed : 3000
}

export const loadTrustGraphMcpConfig = Effect.fn("loadTrustGraphMcpConfig")(function*(
  options: TrustGraphMcpOptions = {},
) {
  const gatewayUrl = O.getOrUndefined(yield* Config.string("GATEWAY_URL").pipe(Config.option))
  const user = O.getOrUndefined(yield* Config.string("USER_ID").pipe(Config.option))
  const gatewaySecret = O.getOrUndefined(yield* Config.string("GATEWAY_SECRET").pipe(Config.option))
  const token = readNonEmpty(gatewaySecret)
  const flowId = O.getOrUndefined(yield* Config.string("FLOW_ID").pipe(Config.option))
  const port = O.getOrUndefined(yield* Config.string("PORT").pipe(Config.option))

  return {
    gatewayUrl: options.gatewayUrl ?? gatewayUrl ?? "ws://localhost:8088/api/v1/rpc",
    user: options.user ?? user ?? "mcp",
    token: options.token ?? token,
    flowId: options.flowId ?? flowId ?? "default",
    name: options.name ?? "trustgraph",
    version: options.version ?? "0.1.0",
    mcpPath: options.mcpPath ?? "/mcp",
    port: options.port ?? parsePort(readNonEmpty(port)),
  }
})

export class TrustGraphMcpConfig extends Context.Service<TrustGraphMcpConfig, TrustGraphMcpConfigShape>()(
  "@trustgraph/mcp/server-effect/TrustGraphMcpConfig",
) {
  static readonly layer = (options: TrustGraphMcpOptions = {}) =>
    Layer.effect(
      TrustGraphMcpConfig,
      loadTrustGraphMcpConfig(options).pipe(Effect.map(TrustGraphMcpConfig.of)),
    )
}

export class TrustGraphGateway extends Context.Service<TrustGraphGateway, TrustGraphGatewayClient>()(
  "@trustgraph/mcp/server-effect/TrustGraphGateway",
) {
  static readonly layer = Layer.effect(
    TrustGraphGateway,
    Effect.gen(function*() {
      const config = yield* TrustGraphMcpConfig
      const client = yield* makeTrustGraphGatewayClientScoped({url: gatewayUrlWithToken(config)})
      return TrustGraphGateway.of(client)
    }),
  )
}

const toErrorMessage = (cause: unknown): string => {
  if (Predicate.isError(cause) && cause.message.length > 0) {
    return cause.message
  }
  if (typeof cause === "string" && cause.length > 0) {
    return cause
  }
  if (Predicate.isObject(cause) && Predicate.hasProperty(cause, "message") && Predicate.isString(cause.message) && cause.message.length > 0) {
    return cause.message
  }
  return "TrustGraph MCP tool failed"
}

const asRecord = (value: unknown): Record<string, unknown> =>
  Predicate.isObject(value) && !Array.isArray(value) ? value as Record<string, unknown> : {}

const stringProperty = (source: unknown, key: string): string | undefined => {
  const value = asRecord(source)[key]
  return Predicate.isString(value) ? value : undefined
}

const booleanProperty = (source: unknown, key: string): boolean | undefined => {
  const value = asRecord(source)[key]
  return typeof value === "boolean" ? value : undefined
}

const responseErrorMessage = (source: unknown): string | undefined => {
  const error = asRecord(source).error
  if (Predicate.isString(error)) return error
  return stringProperty(error, "message")
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

const dispatchGlobal = <E>(
  gateway: TrustGraphGatewayClient,
  service: string,
  request: Record<string, unknown>,
  makeError: (cause: unknown) => E,
  options: {readonly timeoutMs?: number; readonly retries?: number} = {},
) =>
  gateway.dispatch({scope: "global", service, request}, options).pipe(
    Effect.map(asRecord),
    Effect.mapError(makeError),
  )

const dispatchFlow = <E>(
  gateway: TrustGraphGatewayClient,
  config: TrustGraphMcpConfigShape,
  service: string,
  request: Record<string, unknown>,
  makeError: (cause: unknown) => E,
  options: {readonly timeoutMs?: number; readonly retries?: number} = {},
) =>
  gateway.dispatch({
    scope: "flow",
    flow: config.flowId,
    service,
    request,
  }, options).pipe(
    Effect.map(asRecord),
    Effect.mapError(makeError),
  )

const runAgentTool = Effect.fn("TrustGraphMcpToolkit.agent")(function*(
  gateway: TrustGraphGatewayClient,
  config: TrustGraphMcpConfigShape,
  question: string,
) {
  let fullAnswer = ""
  let streamError: AgentError | undefined

  yield* gateway.runDispatchStream(
    {
      scope: "flow",
      flow: config.flowId,
      service: "agent",
      request: {
        question,
        user: config.user,
        collection: "default",
        streaming: true,
      },
    },
    (chunk) => {
      const resp = asRecord(chunk.response)
      const chunkType = stringProperty(resp, "chunk_type")
      const error = chunkType === "error"
        ? responseErrorMessage(resp) ?? "Unknown agent error"
        : responseErrorMessage(resp)
      if (error !== undefined) {
        streamError = AgentError.make({message: error})
        return true
      }

      if (chunkType === "answer" || chunkType === "final-answer") {
        fullAnswer += stringProperty(resp, "content") ?? ""
      }

      return chunk.complete === true || booleanProperty(resp, "end_of_dialog") === true
    },
    {timeoutMs: 120_000, retries: 2},
  ).pipe(
    Effect.mapError((cause) => AgentError.make({message: toErrorMessage(cause)})),
  )

  if (streamError !== undefined) {
    return yield* streamError
  }
  return AgentSuccess.make({text: fullAnswer})
})

export const TrustGraphMcpToolkitLive = TrustGraphMcpToolkit.toLayer(
  Effect.gen(function*() {
    const config = yield* TrustGraphMcpConfig
    const gateway = yield* TrustGraphGateway

    return TrustGraphMcpToolkit.of({
      text_completion: ({system, prompt}) =>
        dispatchFlow(
          gateway,
          config,
          "text-completion",
          {system, prompt},
          (cause) => TextCompletionError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 30_000},
        ).pipe(
          Effect.map((response) => TextCompletionSuccess.make({text: stringProperty(response, "response") ?? ""})),
        ),

      graph_rag: ({query, entity_limit, triple_limit, collection}) =>
        dispatchFlow(
          gateway,
          config,
          "graph-rag",
          {
            query,
            user: config.user,
            collection: collection ?? "default",
            ...(entity_limit !== undefined ? {"entity-limit": entity_limit} : {}),
            ...(triple_limit !== undefined ? {"triple-limit": triple_limit} : {}),
          },
          (cause) => GraphRagError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 60_000},
        ).pipe(
          Effect.map((response) => GraphRagSuccess.make({text: stringProperty(response, "response") ?? ""})),
        ),

      document_rag: ({query, doc_limit, collection}) =>
        dispatchFlow(
          gateway,
          config,
          "document-rag",
          {
            query,
            user: config.user,
            collection: collection ?? "default",
            ...(doc_limit !== undefined ? {"doc-limit": doc_limit} : {}),
          },
          (cause) => DocumentRagError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 60_000},
        ).pipe(
          Effect.map((response) => DocumentRagSuccess.make({text: stringProperty(response, "response") ?? ""})),
        ),

      agent: ({question}) => runAgentTool(gateway, config, question),

      embeddings: ({text}) =>
        dispatchFlow(
          gateway,
          config,
          "embeddings",
          {texts: [...text]},
          (cause) => EmbeddingsError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 30_000},
        ).pipe(
          Effect.map((response) => EmbeddingsSuccess.make({
            vectors: Array.isArray(response.vectors) ? response.vectors as number[][] : [],
          })),
        ),

      triples_query: ({s, p, o, limit, collection}) =>
        dispatchFlow(
          gateway,
          config,
          "triples",
          {
            limit: limit ?? 20,
            user: config.user,
            collection: collection ?? "default",
            ...(asIriTerm(s) !== undefined ? {s: asIriTerm(s)} : {}),
            ...(asIriTerm(p) !== undefined ? {p: asIriTerm(p)} : {}),
            ...(asIriTerm(o) !== undefined ? {o: asIriTerm(o)} : {}),
          },
          (cause) => TriplesQueryError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 30_000},
        ).pipe(
          Effect.map((response) => TriplesQuerySuccess.make({
            triples: Array.isArray(response.triples ?? response.response)
              ? (response.triples ?? response.response) as ClientTriple[]
              : [],
          })),
        ),

      graph_embeddings_query: ({query, limit, collection}) =>
        dispatchFlow(
          gateway,
          config,
          "embeddings",
          {texts: [query]},
          (cause) => GraphEmbeddingsQueryError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 30_000},
        ).pipe(
          Effect.flatMap((embeddingResponse) => {
            const vectors = Array.isArray(embeddingResponse.vectors) ? embeddingResponse.vectors : []
            const firstVector = Array.isArray(vectors[0]) ? vectors[0] as number[] : []
            return dispatchFlow(
              gateway,
              config,
              "graph-embeddings",
              {
                vector: firstVector,
                limit: limit ?? 10,
                user: config.user,
                collection: collection ?? "default",
              },
              (cause) => GraphEmbeddingsQueryError.make({message: toErrorMessage(cause)}),
              {timeoutMs: 30_000},
            )
          }),
          Effect.map((response) => GraphEmbeddingsQuerySuccess.make({
            entities: Array.isArray(response.entities) ? response.entities as ClientEntityMatch[] : [],
          })),
        ),

      get_config_all: () =>
        dispatchGlobal(
          gateway,
          "config",
          {operation: "config"},
          (cause) => GetConfigAllError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 60_000},
        ).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => GetConfigAllError.make({message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((config) => GetConfigAllSuccess.make({config})),
            )
          ),
        ),

      get_config: ({keys}) =>
        dispatchGlobal(
          gateway,
          "config",
          {operation: "get", keys: keys.map(({type, key}) => ({type, key}))},
          (cause) => GetConfigError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 60_000},
        ).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => GetConfigError.make({message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((config) => GetConfigSuccess.make({config})),
            )
          ),
        ),

      put_config: ({values}) =>
        dispatchGlobal(
          gateway,
          "config",
          {operation: "put", values: values.map(({type, key, value}) => ({type, key, value}))},
          (cause) => PutConfigError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 60_000},
        ).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => PutConfigError.make({message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => PutConfigSuccess.make({response})),
            )
          ),
        ),

      delete_config: ({type, key}) =>
        dispatchGlobal(
          gateway,
          "config",
          {operation: "delete", keys: [{type, key}]},
          (cause) => DeleteConfigError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 30_000},
        ).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => DeleteConfigError.make({message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => DeleteConfigSuccess.make({response})),
            )
          ),
        ),

      get_flows: () =>
        dispatchGlobal(
          gateway,
          "flow",
          {operation: "list-flows"},
          (cause) => GetFlowsError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 60_000},
        ).pipe(
          Effect.map((response) => GetFlowsSuccess.make({
            flow_ids: Array.isArray(response["flow-ids"]) ? response["flow-ids"] as string[] : [],
          })),
        ),

      get_flow: ({flow_id}) =>
        dispatchGlobal(
          gateway,
          "flow",
          {operation: "get-flow", "flow-id": flow_id},
          (cause) => GetFlowError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 60_000},
        ).pipe(
          Effect.flatMap((response) =>
            decodeJsonOrFail(
              response.flow,
              (cause) => GetFlowError.make({message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((flow) => GetFlowSuccess.make({flow})),
            )
          ),
        ),

      start_flow: ({flow_id, blueprint_name, description, parameters}) =>
        dispatchGlobal(
          gateway,
          "flow",
          {
            operation: "start-flow",
            "flow-id": flow_id,
            "blueprint-name": blueprint_name,
            description,
            ...(parameters === undefined ? {} : {parameters: {...parameters}}),
          },
          (cause) => StartFlowError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 30_000},
        ).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => StartFlowError.make({message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => StartFlowSuccess.make({response})),
            )
          ),
        ),

      stop_flow: ({flow_id}) =>
        dispatchGlobal(
          gateway,
          "flow",
          {operation: "stop-flow", "flow-id": flow_id},
          (cause) => StopFlowError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 30_000},
        ).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => StopFlowError.make({message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => StopFlowSuccess.make({response})),
            )
          ),
        ),

      get_documents: () =>
        dispatchGlobal(
          gateway,
          "librarian",
          {operation: "list-documents", user: config.user},
          (cause) => GetDocumentsError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 60_000},
        ).pipe(
          Effect.flatMap((value) =>
            decodeJsonArrayOrFail(
              value["document-metadatas"] ?? value.documents ?? [],
              (cause) => GetDocumentsError.make({message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((documents) => GetDocumentsSuccess.make({documents})),
            )
          ),
        ),

      load_document: Effect.fn("TrustGraphMcpToolkit.load_document")(function*({document, mime_type, title, comments, tags, id}) {
          const timestamp = yield* Clock.currentTimeMillis
          const metadata = {
            time: Math.floor(timestamp / 1000),
            kind: mime_type,
            title,
            comments: comments ?? "",
            user: config.user,
            tags: tags === undefined ? [] : [...tags],
            "document-type": "source",
            documentType: "source",
            ...(id === undefined ? {} : {id}),
          }
          const value = yield* dispatchGlobal(
            gateway,
            "librarian",
            {
              operation: "add-document",
              "document-metadata": metadata,
              documentMetadata: metadata,
              content: document,
            },
            (cause) => LoadDocumentError.make({message: toErrorMessage(cause)}),
            {timeoutMs: 30_000},
          )
          return yield* decodeJsonOrFail(
            value,
            (cause) => LoadDocumentError.make({message: toErrorMessage(cause)}),
          ).pipe(
            Effect.map((response) => LoadDocumentSuccess.make({response})),
          )
        }),

      remove_document: ({id, collection}) =>
        dispatchGlobal(
          gateway,
          "librarian",
          {
            operation: "remove-document",
            "document-id": id,
            documentId: id,
            user: config.user,
            collection: collection ?? "default",
          },
          (cause) => RemoveDocumentError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 30_000},
        ).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => RemoveDocumentError.make({message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => RemoveDocumentSuccess.make({response})),
            )
          ),
        ),

      get_prompts: () =>
        dispatchGlobal(
          gateway,
          "config",
          {operation: "config"},
          (cause) => GetPromptsError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 60_000},
        ).pipe(
          Effect.map((response) => {
            const promptNs = asRecord(asRecord(response.config).prompt)
            const prompts = Object.keys(promptNs)
              .filter((key) => key !== "system")
              .sort()
              .map((id) => ({id, name: id}))
            return GetPromptsSuccess.make({prompts})
          }),
        ),

      get_prompt: ({id}) =>
        dispatchGlobal(
          gateway,
          "config",
          {operation: "config"},
          (cause) => GetPromptError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 60_000},
        ).pipe(
          Effect.flatMap((response) =>
            decodeJsonOrFail(
              asRecord(asRecord(response.config).prompt)[id] ?? null,
              (cause) => GetPromptError.make({message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((prompt) => GetPromptSuccess.make({prompt})),
            )
          ),
        ),

      get_knowledge_cores: () =>
        dispatchGlobal(
          gateway,
          "knowledge",
          {operation: "list-kg-cores", user: config.user},
          (cause) => GetKnowledgeCoresError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 60_000},
        ).pipe(
          Effect.map((response) => GetKnowledgeCoresSuccess.make({
            ids: Array.isArray(response.ids) ? response.ids as string[] : [],
          })),
        ),

      delete_kg_core: ({id, collection}) =>
        dispatchGlobal(
          gateway,
          "knowledge",
          {
            operation: "delete-kg-core",
            id,
            user: config.user,
            collection: collection ?? "default",
          },
          (cause) => DeleteKgCoreError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 30_000},
        ).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => DeleteKgCoreError.make({message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => DeleteKgCoreSuccess.make({response})),
            )
          ),
        ),

      load_kg_core: ({id, flow, collection}) =>
        dispatchGlobal(
          gateway,
          "knowledge",
          {
            operation: "load-kg-core",
            id,
            flow,
            user: config.user,
            collection: collection ?? "default",
          },
          (cause) => LoadKgCoreError.make({message: toErrorMessage(cause)}),
          {timeoutMs: 30_000},
        ).pipe(
          Effect.flatMap((value) =>
            decodeJsonOrFail(
              value,
              (cause) => LoadKgCoreError.make({message: toErrorMessage(cause)}),
            ).pipe(
              Effect.map((response) => LoadKgCoreSuccess.make({response})),
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

const makeTrustGraphMcpHttpLayerFromConfig = (
  config: TrustGraphMcpConfigShape,
) => {
  const tools = makeTrustGraphMcpToolkitLayer()

  return Layer.mergeAll(
    TrustGraphMcpHttpApiRoutes,
    tools,
  ).pipe(
    Layer.provide(McpServer.layerHttp({
      name: config.name,
      version: config.version,
      path: config.mcpPath,
    })),
    Layer.provide(TrustGraphGateway.layer),
    Layer.provide(Layer.succeed(TrustGraphMcpConfig, TrustGraphMcpConfig.of(config))),
  )
}

const makeTrustGraphMcpToolkitLayer = () =>
  McpServer.toolkit(TrustGraphMcpToolkit).pipe(
    Layer.provide(TrustGraphMcpToolkitLive),
  )

const makeTrustGraphMcpStdioLayerFromConfig = (
  config: TrustGraphMcpConfigShape,
) =>
  makeTrustGraphMcpToolkitLayer().pipe(
    Layer.provide(McpServer.layerStdio({
      name: config.name,
      version: config.version,
    })),
    Layer.provide(NodeStdio.layer),
    Layer.provide(TrustGraphGateway.layer),
    Layer.provide(Layer.succeed(TrustGraphMcpConfig, TrustGraphMcpConfig.of(config))),
  )

export const makeTrustGraphMcpHttpServerLayer = (
  options: TrustGraphMcpOptions = {},
) =>
  Layer.unwrap(
    loadTrustGraphMcpConfig(options).pipe(
      Effect.map((config) =>
        HttpRouter.serve(makeTrustGraphMcpHttpLayerFromConfig(config)).pipe(
          Layer.provide(BunHttpServer.layer({port: config.port})),
        )
      ),
    ),
  )

export const makeTrustGraphMcpHttpLayer = (
  options: TrustGraphMcpOptions = {},
) =>
  Layer.unwrap(
    loadTrustGraphMcpConfig(options).pipe(
      Effect.map(makeTrustGraphMcpHttpLayerFromConfig),
    ),
  )

export const makeTrustGraphMcpStdioLayer = (
  options: TrustGraphMcpOptions = {},
) =>
  Layer.unwrap(
    loadTrustGraphMcpConfig(options).pipe(
      Effect.map(makeTrustGraphMcpStdioLayerFromConfig),
    ),
  )

export const runHttp = (options: TrustGraphMcpOptions = {}): void => {
  Layer.launch(makeTrustGraphMcpHttpServerLayer(options)).pipe(BunRuntime.runMain)
}

export const runStdio = (options: TrustGraphMcpOptions = {}): void => {
  Layer.launch(makeTrustGraphMcpStdioLayer(options)).pipe(NodeRuntime.runMain)
}
