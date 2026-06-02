/**
 * Chunking service — splits text documents into chunks for downstream processing.
 *
 * A FlowProcessor that:
 * 1. Consumes TextDocument messages
 * 2. Splits text using recursive character text splitting
 * 3. Emits Chunk messages for each resulting chunk
 *
 * Python reference: trustgraph-flow/trustgraph/chunking/recursive_splitter/service.py
 */

import {
  makeFlowProcessor,
  makeConsumerSpec,
  makeProducerSpec,
  makeParameterSpec,
  type ProcessorConfig,
  type FlowProcessorRuntime,
  type FlowContext,
  type FlowResourceNotFoundError,
  type MessagingDeliveryError,
  type TextDocument,
  type Chunk,
  type Triples,
  type Spec,
} from "@trustgraph/base";
import { makeFlowProcessorProgram } from "@trustgraph/base";
import { Effect } from "effect";
import { recursiveSplit } from "./recursive-splitter.js";

const DEFAULT_CHUNK_SIZE = 2000;
const DEFAULT_CHUNK_OVERLAP = 100;

const onChunkMessage = Effect.fn("ChunkingService.onMessage")(function* (
  msg: TextDocument,
  properties: Record<string, string>,
  flowCtx: FlowContext,
) {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const chunkSize = yield* flowCtx.flow.parameterEffect<number>("chunk-size").pipe(
    Effect.orElseSucceed(() => DEFAULT_CHUNK_SIZE),
  );
  const chunkOverlap = yield* flowCtx.flow.parameterEffect<number>("chunk-overlap").pipe(
    Effect.orElseSucceed(() => DEFAULT_CHUNK_OVERLAP),
  );

  const text = msg.text;
  if (text.trim().length === 0) {
    yield* Effect.logWarning(`[ChunkingService] Empty text received for document ${msg.documentId}`);
    return;
  }

  const chunks = recursiveSplit(text, chunkSize, chunkOverlap);

  yield* Effect.log(
    `[ChunkingService] Split document ${msg.documentId} into ${chunks.length} chunks (size=${chunkSize}, overlap=${chunkOverlap})`,
  );

  const outputProducer = yield* flowCtx.flow.producerEffect<Chunk>("chunk-output");

  yield* Effect.forEach(
    chunks,
    (chunkText) =>
      outputProducer.send(requestId, {
        metadata: msg.metadata,
        chunk: chunkText,
        documentId: msg.documentId,
      }),
    { discard: true },
  );
});

export const makeChunkingSpecs = (): ReadonlyArray<
  Spec<never>
> => [
  makeConsumerSpec<TextDocument, FlowResourceNotFoundError | MessagingDeliveryError>(
    "chunk-input",
    onChunkMessage,
  ),
  makeProducerSpec<Chunk>("chunk-output"),
  makeProducerSpec<Triples>("chunk-triples"),
  makeParameterSpec("chunk-size"),
  makeParameterSpec("chunk-overlap"),
];

export type ChunkingService = FlowProcessorRuntime;

export function makeChunkingService(config: ProcessorConfig): ChunkingService {
  const service = makeFlowProcessor(config, {
    specifications: makeChunkingSpecs(),
  });
  Effect.runSync(Effect.log("[ChunkingService] Service initialized"));
  return service;
}

export const ChunkingService = makeChunkingService;

export const program = makeFlowProcessorProgram({
  id: "chunking",
  specs: () => makeChunkingSpecs(),
});

export function run(): Promise<void> {
  return Effect.runPromise(program);
}
