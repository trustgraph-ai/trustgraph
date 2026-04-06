/**
 * Topic naming conventions.
 *
 * Python reference: trustgraph-base/trustgraph/schema/core/topic.py
 *
 * The Python version uses Pulsar URI format: "q1/tg/flow/queue-name"
 * We use NATS subject format: "tg.flow.queue-name"
 */

export type QoS = "q0" | "q1" | "q2";

export function topic(
  name: string,
  tenant = "tg",
  namespace = "flow",
): string {
  return `${tenant}.${namespace}.${name}`;
}

// Well-known topics from the Python schema
export const topics = {
  // Config
  configRequest: topic("config-request"),
  configResponse: topic("config-response"),
  configPush: topic("config-push"),

  // Text completion
  textCompletionRequest: topic("text-completion-request"),
  textCompletionResponse: topic("text-completion-response"),

  // Embeddings
  embeddingsRequest: topic("embeddings-request"),
  embeddingsResponse: topic("embeddings-response"),

  // Graph RAG
  graphRagRequest: topic("graph-rag-request"),
  graphRagResponse: topic("graph-rag-response"),

  // Document RAG
  documentRagRequest: topic("document-rag-request"),
  documentRagResponse: topic("document-rag-response"),

  // Agent
  agentRequest: topic("agent-request"),
  agentResponse: topic("agent-response"),

  // Triples
  triplesRequest: topic("triples-request"),
  triplesResponse: topic("triples-response"),

  // Graph embeddings
  graphEmbeddingsRequest: topic("graph-embeddings-request"),
  graphEmbeddingsResponse: topic("graph-embeddings-response"),

  // Document embeddings
  docEmbeddingsRequest: topic("doc-embeddings-request"),
  docEmbeddingsResponse: topic("doc-embeddings-response"),

  // Prompt
  promptRequest: topic("prompt-request"),
  promptResponse: topic("prompt-response"),

  // Librarian (document management)
  librarianRequest: topic("librarian-request"),
  librarianResponse: topic("librarian-response"),

  // Knowledge core management
  knowledgeRequest: topic("knowledge-request"),
  knowledgeResponse: topic("knowledge-response"),

  // Collection management
  collectionManagementRequest: topic("collection-management-request"),
  collectionManagementResponse: topic("collection-management-response"),

  // Flow management
  flowRequest: topic("flow-request"),
  flowResponse: topic("flow-response"),
} as const;
