/**
 * Graph RAG service.
 *
 * Consumes GraphRagRequest messages from the agent/gateway, runs the full
 * Graph RAG pipeline, and emits GraphRagResponse.
 *
 * Python reference: trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py
 */

import {
  makeConsumerSpec,
  makeFlowProcessor,
  makeProducerSpec,
  makeRequestResponseSpec,
  makeFlowProcessorProgram,
  type EffectRequestOptions,
  type EffectRequestResponse,
  type FlowContext,
  type FlowProcessorRuntime,
  type FlowRequestOptions,
  type FlowRequestor,
  type FlowResourceNotFoundError,
  type GraphEmbeddingsRequest,
  type GraphEmbeddingsResponse,
  type GraphRagRequest,
  type GraphRagResponse,
  type EmbeddingsRequest,
  type EmbeddingsResponse,
  type MessagingDeliveryError,
  type ProcessorConfig,
  type PromptRequest,
  type PromptResponse,
  type Spec,
  type TextCompletionRequest,
  type TextCompletionResponse,
  type TriplesQueryRequest,
  type TriplesQueryResponse,
} from "@trustgraph/base";
import { Effect } from "effect";
import {
  GraphRagEngine,
  GraphRagEngineError,
  GraphRagLive,
  makeGraphRagEngine,
  type GraphRagClients,
  type GraphRagConfig,
} from "./graph-rag.js";

const toEffectRequestOptions = <TRes>(
  options: FlowRequestOptions<TRes> | undefined,
): EffectRequestOptions<TRes> | undefined => {
  if (options === undefined) return undefined;
  return {
    ...(options.timeoutMs === undefined ? {} : { timeoutMs: options.timeoutMs }),
    ...(options.recipient === undefined
      ? {}
      : {
          recipient: (response: TRes) =>
            Effect.promise(() => options.recipient?.(response) ?? Promise.resolve(true)),
        }),
  };
};

const toPromiseRequestor = <TReq, TRes>(
  requestor: EffectRequestResponse<TReq, TRes>,
): FlowRequestor<TReq, TRes> => ({
  request: (request, options) =>
    Effect.runPromise(requestor.request(request, toEffectRequestOptions(options))),
  stop: () => Effect.runPromise(requestor.stop),
});

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

  const producer = yield* flowCtx.flow.producerEffect<GraphRagResponse>("graph-rag-response");
  const engine = yield* GraphRagEngine;

  yield* Effect.log(`[GraphRagService] Received request ${requestId}: "${msg.query?.slice(0, 60)}..." collection=${msg.collection}`);

  const clients: GraphRagClients = {
    llm: toPromiseRequestor(yield* flowCtx.flow.requestorEffect<TextCompletionRequest, TextCompletionResponse>("llm")),
    embeddings: toPromiseRequestor(yield* flowCtx.flow.requestorEffect<EmbeddingsRequest, EmbeddingsResponse>("embeddings")),
    graphEmbeddings: toPromiseRequestor(
      yield* flowCtx.flow.requestorEffect<GraphEmbeddingsRequest, GraphEmbeddingsResponse>("graph-embeddings"),
    ),
    triples: toPromiseRequestor(yield* flowCtx.flow.requestorEffect<TriplesQueryRequest, TriplesQueryResponse>("triples")),
    prompt: toPromiseRequestor(yield* flowCtx.flow.requestorEffect<PromptRequest, PromptResponse>("prompt")),
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

  const response: GraphRagResponse = {
    response: result.answer,
    endOfStream: true,
  };

  if (result.subgraph.length > 0) {
    (response as Record<string, unknown>).message_type = "explain";
    (response as Record<string, unknown>).explain_id = `explain-${requestId}`;
    (response as Record<string, unknown>).explain_triples = result.subgraph;
  }

  yield* producer.send(requestId, response);
});

export const makeGraphRagSpecs = (): ReadonlyArray<Spec<GraphRagEngine>> => [
  makeConsumerSpec<GraphRagRequest, FlowResourceNotFoundError | MessagingDeliveryError, GraphRagEngine>(
    "graph-rag-request",
    onGraphRagRequest,
  ),
  makeProducerSpec<GraphRagResponse>("graph-rag-response"),
  makeRequestResponseSpec<TextCompletionRequest, TextCompletionResponse>(
    "llm",
    "text-completion-request",
    "text-completion-response",
  ),
  makeRequestResponseSpec<EmbeddingsRequest, EmbeddingsResponse>(
    "embeddings",
    "embeddings-request",
    "embeddings-response",
  ),
  makeRequestResponseSpec<GraphEmbeddingsRequest, GraphEmbeddingsResponse>(
    "graph-embeddings",
    "graph-embeddings-request",
    "graph-embeddings-response",
  ),
  makeRequestResponseSpec<TriplesQueryRequest, TriplesQueryResponse>(
    "triples",
    "triples-request",
    "triples-response",
  ),
  makeRequestResponseSpec<PromptRequest, PromptResponse>(
    "prompt",
    "prompt-request",
    "prompt-response",
  ),
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

export function run(): Promise<void> {
  return Effect.runPromise(program);
}
