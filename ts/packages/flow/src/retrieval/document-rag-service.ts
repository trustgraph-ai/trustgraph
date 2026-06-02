/**
 * Document RAG service.
 *
 * Consumes DocumentRagRequest messages, runs the document retrieval pipeline,
 * and emits DocumentRagResponse.
 *
 * Python reference: trustgraph-flow/trustgraph/retrieval/document_rag/
 */

import {
  makeConsumerSpec,
  makeFlowProcessor,
  makeProducerSpec,
  makeRequestResponseSpec,
  makeFlowProcessorProgram,
  type DocumentEmbeddingsRequest,
  type DocumentEmbeddingsResponse,
  type DocumentRagRequest,
  type DocumentRagResponse,
  type EffectRequestOptions,
  type EffectRequestResponse,
  type EmbeddingsRequest,
  type EmbeddingsResponse,
  type FlowContext,
  type FlowProcessorRuntime,
  type FlowRequestOptions,
  type FlowRequestor,
  type FlowResourceNotFoundError,
  type MessagingDeliveryError,
  type ProcessorConfig,
  type PromptRequest,
  type PromptResponse,
  type Spec,
  type TextCompletionRequest,
  type TextCompletionResponse,
} from "@trustgraph/base";
import { Effect } from "effect";
import {
  DocumentRagEngine,
  DocumentRagEngineError,
  DocumentRagLive,
  makeDocumentRagEngine,
  type DocumentRagClients,
} from "./document-rag.js";

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

const onDocumentRagRequest = Effect.fn("DocumentRagService.onRequest")(function* (
  msg: DocumentRagRequest,
  properties: Record<string, string>,
  flowCtx: FlowContext<DocumentRagEngine>,
) {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const producer = yield* flowCtx.flow.producerEffect<DocumentRagResponse>("document-rag-response");
  const engine = yield* DocumentRagEngine;

  const clients: DocumentRagClients = {
    llm: toPromiseRequestor(yield* flowCtx.flow.requestorEffect<TextCompletionRequest, TextCompletionResponse>("llm")),
    embeddings: toPromiseRequestor(yield* flowCtx.flow.requestorEffect<EmbeddingsRequest, EmbeddingsResponse>("embeddings")),
    docEmbeddings: toPromiseRequestor(
      yield* flowCtx.flow.requestorEffect<DocumentEmbeddingsRequest, DocumentEmbeddingsResponse>("doc-embeddings"),
    ),
    prompt: toPromiseRequestor(yield* flowCtx.flow.requestorEffect<PromptRequest, PromptResponse>("prompt")),
  };

  const response = yield* engine.query(
    clients,
    msg.query,
    {
      ...(msg.collection !== undefined ? { collection: msg.collection } : {}),
    },
  ).pipe(
    Effect.catch((error: DocumentRagEngineError) =>
      Effect.logError("[DocumentRag] Query failed", {
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

  if (response === undefined) return;
  yield* producer.send(requestId, { response, endOfStream: true });
});

export const makeDocumentRagSpecs = (): ReadonlyArray<Spec<DocumentRagEngine>> => [
  makeConsumerSpec<DocumentRagRequest, FlowResourceNotFoundError | MessagingDeliveryError, DocumentRagEngine>(
    "document-rag-request",
    onDocumentRagRequest,
  ),
  makeProducerSpec<DocumentRagResponse>("document-rag-response"),
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
  makeRequestResponseSpec<DocumentEmbeddingsRequest, DocumentEmbeddingsResponse>(
    "doc-embeddings",
    "document-embeddings-request",
    "document-embeddings-response",
  ),
  makeRequestResponseSpec<PromptRequest, PromptResponse>(
    "prompt",
    "prompt-request",
    "prompt-response",
  ),
];

export type DocumentRagService = FlowProcessorRuntime<DocumentRagEngine>;

export function makeDocumentRagService(config: ProcessorConfig): DocumentRagService {
  return makeFlowProcessor(config, {
    specifications: makeDocumentRagSpecs(),
    provide: (effect) =>
      effect.pipe(
        Effect.provideService(DocumentRagEngine, DocumentRagEngine.of(makeDocumentRagEngine())),
      ),
  });
}

export const DocumentRagService = makeDocumentRagService;

export const program = makeFlowProcessorProgram({
  id: "document-rag",
  specs: makeDocumentRagSpecs,
  layer: () => DocumentRagLive,
});

export function run(): Promise<void> {
  return Effect.runPromise(program);
}
