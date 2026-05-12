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
  FlowProcessor,
  ConsumerSpec,
  ProducerSpec,
  ParameterSpec,
  type ProcessorConfig,
  type FlowContext,
  type FlowResourceNotFoundError,
  type MessagingDeliveryError,
  type TextDocument,
  type Chunk,
  type Triples,
} from "@trustgraph/base";
import { makeProcessorProgram } from "@trustgraph/base";
import { Effect } from "effect";
import { recursiveSplit } from "./recursive-splitter.js";

const DEFAULT_CHUNK_SIZE = 2000;
const DEFAULT_CHUNK_OVERLAP = 100;

export class ChunkingService extends FlowProcessor {
  constructor(config: ProcessorConfig) {
    super(config);

    this.registerSpecification(
      new ConsumerSpec<TextDocument, FlowResourceNotFoundError | MessagingDeliveryError>(
        "chunk-input",
        this.onMessageEffect.bind(this),
      ),
    );
    this.registerSpecification(new ProducerSpec<Chunk>("chunk-output"));
    this.registerSpecification(new ProducerSpec<Triples>("chunk-triples"));
    this.registerSpecification(new ParameterSpec("chunk-size"));
    this.registerSpecification(new ParameterSpec("chunk-overlap"));

    console.log("[ChunkingService] Service initialized");
  }

  private onMessageEffect(
    msg: TextDocument,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ) {
    return Effect.gen(function* () {
      const requestId = properties.id;
      if (requestId === undefined || requestId.length === 0) return;

      const chunkSize = yield* flowCtx.flow.parameterEffect<number>("chunk-size").pipe(
        Effect.catch(() => Effect.succeed(DEFAULT_CHUNK_SIZE)),
      );
      const chunkOverlap = yield* flowCtx.flow.parameterEffect<number>("chunk-overlap").pipe(
        Effect.catch(() => Effect.succeed(DEFAULT_CHUNK_OVERLAP)),
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
  }
}

export const program = makeProcessorProgram({
  id: "chunking",
  make: (config) => new ChunkingService(config),
});

export async function run(): Promise<void> {
  await ChunkingService.launch("chunking");
}
