/**
 * Graph RAG service.
 *
 * Consumes GraphRagRequest messages from the agent/gateway, runs the full
 * Graph RAG pipeline, and emits GraphRagResponse.
 *
 * Python reference: trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py
 */

import {NodeRuntime} from "@effect/platform-node";
import type {
  FlowContext,
  FlowProcessorRuntime,
  FlowResourceNotFoundError,
  GraphEmbeddingsRequest,
  GraphEmbeddingsResponse,
  GraphRagRequest,
  GraphRagResponse,
  EmbeddingsRequest,
  EmbeddingsResponse,
  MessagingDeliveryError,
  ProcessorConfig,
  PromptRequest,
  PromptResponse,
  Spec,
  TextCompletionRequest,
  TextCompletionResponse,
  TriplesQueryRequest,
  TriplesQueryResponse,
} from "@trustgraph/base";
import {
  makeConsumerSpec,
  makeFlowProcessor,
  makeProducerSpec,
  makeRequestResponseSpec,
  makeFlowProcessorProgram,
} from "@trustgraph/base";
import {Effect} from "effect";
import type {
  GraphRagEngineError,
  GraphRagClients,
  GraphRagConfig,
} from "./graph-rag.js";
import {
  GraphRagEngine,
  GraphRagLive,
  makeGraphRagEngine,
} from "./graph-rag.js";

const GraphRagResponseProducer = makeProducerSpec<GraphRagResponse>("graph-rag-response");
const GraphRagLlmClient = makeRequestResponseSpec<TextCompletionRequest, TextCompletionResponse>(
  "llm",
  "text-completion-request",
  "text-completion-response",
);
const GraphRagEmbeddingsClient = makeRequestResponseSpec<EmbeddingsRequest, EmbeddingsResponse>(
  "embeddings",
  "embeddings-request",
  "embeddings-response",
);
const GraphRagGraphEmbeddingsClient = makeRequestResponseSpec<GraphEmbeddingsRequest, GraphEmbeddingsResponse>(
  "graph-embeddings",
  "graph-embeddings-request",
  "graph-embeddings-response",
);
const GraphRagTriplesClient = makeRequestResponseSpec<TriplesQueryRequest, TriplesQueryResponse>(
  "triples",
  "triples-request",
  "triples-response",
);
const GraphRagPromptClient = makeRequestResponseSpec<PromptRequest, PromptResponse>(
  "prompt",
  "prompt-request",
  "prompt-response",
);

const graphRagConfigFromRequest = (msg: GraphRagRequest): GraphRagConfig => ({
  ...(msg.entityLimit !== undefined ? { entityLimit: msg.entityLimit } : {}),
  ...(msg.tripleLimit !== undefined ? { tripleLimit: msg.tripleLimit } : {}),
  ...(msg.maxSubgraphSize !== undefined ? { maxSubgraphSize: msg.maxSubgraphSize } : {}),
  ...(msg.maxPathLength !== undefined ? { maxPathLength: msg.maxPathLength } : {}),
});

const onGraphRagRequest = Effect.fn("GraphRagService.onRequest")(function* (
  msg: GraphRagRequest,
  properties: Record<string, string>,
  flowCtx: FlowContext<GraphRagEngine>,
) {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const producer = yield* flowCtx.flow.producerEffect(GraphRagResponseProducer);
  const engine = yield* GraphRagEngine;

  yield* Effect.log(`[GraphRagService] Received request ${requestId}: "${msg.query?.slice(0, 60)}..." collection=${msg.collection}`);

  const clients: GraphRagClients = {
    llm: yield* flowCtx.flow.requestorEffect(GraphRagLlmClient),
    embeddings: yield* flowCtx.flow.requestorEffect(GraphRagEmbeddingsClient),
    graphEmbeddings: yield* flowCtx.flow.requestorEffect(GraphRagGraphEmbeddingsClient),
    triples: yield* flowCtx.flow.requestorEffect(GraphRagTriplesClient),
    prompt: yield* flowCtx.flow.requestorEffect(GraphRagPromptClient),
  };

  const result = yield* engine.query(
    clients,
    msg.query,
    {
      ...(msg.collection !== undefined ? { collection: msg.collection } : {}),
    },
    graphRagConfigFromRequest(msg),
  ).pipe(
    Effect.catch((error: GraphRagEngineError) =>
      Effect.logError("[GraphRag] Query failed", {
        error: error.message,
        operation: error.operation,
      }).pipe(
        Effect.flatMap(() =>
          producer.send(requestId, {
            response: "",
            error: { type: "rag-error", message: error.message },
          }),
        ),
        Effect.as(undefined),
      ),
    ),
  );

  if (result === undefined) return;

  const response: GraphRagResponse = result.subgraph.length === 0
    ? {
        response: result.answer,
        endOfStream: true,
      }
    : {
        response: result.answer,
        endOfStream: true,
        message_type: "explain",
        explain_id: `explain-${requestId}`,
        explain_triples: [...result.subgraph],
      };

  yield* producer.send(requestId, response);
});

export const makeGraphRagSpecs = (): ReadonlyArray<Spec<GraphRagEngine>> => [
  makeConsumerSpec<GraphRagRequest, FlowResourceNotFoundError | MessagingDeliveryError, GraphRagEngine>(
    "graph-rag-request",
    onGraphRagRequest,
  ),
  GraphRagResponseProducer,
  GraphRagLlmClient,
  GraphRagEmbeddingsClient,
  GraphRagGraphEmbeddingsClient,
  GraphRagTriplesClient,
  GraphRagPromptClient,
];

export type GraphRagService = FlowProcessorRuntime<GraphRagEngine>;

export function makeGraphRagService(config: ProcessorConfig): GraphRagService {
  return makeFlowProcessor(config, {
    specifications: makeGraphRagSpecs(),
    provide: (effect) =>
      effect.pipe(
        Effect.provideService(GraphRagEngine, GraphRagEngine.of(makeGraphRagEngine())),
      ),
  });
}

export const GraphRagService = makeGraphRagService;

export const program = makeFlowProcessorProgram({
  id: "graph-rag",
  specs: makeGraphRagSpecs,
  layer: () => GraphRagLive,
});

export function runMain(): void {
  NodeRuntime.runMain(program);
}
