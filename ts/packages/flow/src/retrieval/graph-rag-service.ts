/**
 * Graph RAG service — FlowProcessor wrapper around the GraphRag class.
 *
 * Consumes GraphRagRequest messages from the agent/gateway, runs the full
 * Graph RAG pipeline (concept extraction → entity lookup → graph traversal →
 * edge scoring → answer synthesis), and emits GraphRagResponse.
 *
 * Each request gets its own GraphRag instance to prevent data leakage
 * across requests (security requirement from the Python implementation).
 *
 * Python reference: trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py
 */

import {
  FlowProcessor,
  ConsumerSpec,
  ProducerSpec,
  RequestResponseSpec,
  type ProcessorConfig,
  type FlowContext,
  type GraphRagRequest,
  type GraphRagResponse,
  type TextCompletionRequest,
  type TextCompletionResponse,
  type EmbeddingsRequest,
  type EmbeddingsResponse,
  type GraphEmbeddingsRequest,
  type GraphEmbeddingsResponse,
  type TriplesQueryRequest,
  type TriplesQueryResponse,
  type PromptRequest,
  type PromptResponse,
} from "@trustgraph/base";
import { GraphRag } from "./graph-rag.js";

export class GraphRagService extends FlowProcessor {
  constructor(config: ProcessorConfig) {
    super(config);

    // Consumer: graph RAG requests
    this.registerSpecification(
      new ConsumerSpec<GraphRagRequest>("graph-rag-request", this.onRequest.bind(this)),
    );

    // Producer: graph RAG responses
    this.registerSpecification(new ProducerSpec<GraphRagResponse>("graph-rag-response"));

    // Request-response clients for the pipeline
    this.registerSpecification(
      new RequestResponseSpec<TextCompletionRequest, TextCompletionResponse>(
        "llm",
        "text-completion-request",
        "text-completion-response",
      ),
    );
    this.registerSpecification(
      new RequestResponseSpec<EmbeddingsRequest, EmbeddingsResponse>(
        "embeddings",
        "embeddings-request",
        "embeddings-response",
      ),
    );
    this.registerSpecification(
      new RequestResponseSpec<GraphEmbeddingsRequest, GraphEmbeddingsResponse>(
        "graph-embeddings",
        "graph-embeddings-request",
        "graph-embeddings-response",
      ),
    );
    this.registerSpecification(
      new RequestResponseSpec<TriplesQueryRequest, TriplesQueryResponse>(
        "triples",
        "triples-request",
        "triples-response",
      ),
    );
    this.registerSpecification(
      new RequestResponseSpec<PromptRequest, PromptResponse>(
        "prompt",
        "prompt-request",
        "prompt-response",
      ),
    );

    console.log("[GraphRag] Service initialized");
  }

  private async onRequest(
    msg: GraphRagRequest,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (!requestId) return;

    const producer = flowCtx.flow.producer<GraphRagResponse>("graph-rag-response");
    console.log(`[GraphRagService] Received request ${requestId}: "${msg.query?.slice(0, 60)}..." collection=${msg.collection}`);

    try {
      // Create a per-request GraphRag instance with flow clients
      const graphRag = new GraphRag(
        {
          llm: flowCtx.flow.requestor<TextCompletionRequest, TextCompletionResponse>("llm"),
          embeddings: flowCtx.flow.requestor<EmbeddingsRequest, EmbeddingsResponse>("embeddings"),
          graphEmbeddings: flowCtx.flow.requestor<GraphEmbeddingsRequest, GraphEmbeddingsResponse>("graph-embeddings"),
          triples: flowCtx.flow.requestor<TriplesQueryRequest, TriplesQueryResponse>("triples"),
          prompt: flowCtx.flow.requestor<PromptRequest, PromptResponse>("prompt"),
        },
        {
          entityLimit: msg.entityLimit,
          tripleLimit: msg.tripleLimit,
          maxSubgraphSize: msg.maxSubgraphSize,
          maxPathLength: msg.maxPathLength,
        },
      );

      const result = await graphRag.query(msg.query, {
        collection: msg.collection,
      });

      // Send answer with explain data embedded in a SINGLE message.
      // Non-streaming callers (agent's RequestResponse) return the first
      // response — so the answer must be in that first (and only) message.
      // Streaming callers (gateway) extract explain data + answer from
      // the same message.
      const response: GraphRagResponse = {
        response: result.answer,
        endOfStream: true,
      };

      if (result.subgraph.length > 0) {
        (response as Record<string, unknown>).message_type = "explain";
        (response as Record<string, unknown>).explain_id = `explain-${requestId}`;
        (response as Record<string, unknown>).explain_triples = result.subgraph;
      }

      await producer.send(requestId, response);
    } catch (err) {
      console.error("[GraphRag] Query failed:", err);
      await producer.send(requestId, {
        response: "",
        error: { type: "rag-error", message: String(err) },
      });
    }
  }
}

export async function run(): Promise<void> {
  await GraphRagService.launch("graph-rag");
}
