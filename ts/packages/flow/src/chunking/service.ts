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
  type TextDocument,
  type Chunk,
  type Triples,
} from "@trustgraph/base";
import { recursiveSplit } from "./recursive-splitter.js";

const DEFAULT_CHUNK_SIZE = 2000;
const DEFAULT_CHUNK_OVERLAP = 100;

export class ChunkingService extends FlowProcessor {
  constructor(config: ProcessorConfig) {
    super(config);

    this.registerSpecification(
      new ConsumerSpec<TextDocument>("input", this.onMessage.bind(this)),
    );
    this.registerSpecification(new ProducerSpec<Chunk>("output"));
    this.registerSpecification(new ProducerSpec<Triples>("triples"));
    this.registerSpecification(new ParameterSpec("chunk-size"));
    this.registerSpecification(new ParameterSpec("chunk-overlap"));

    console.log("[ChunkingService] Service initialized");
  }

  private async onMessage(
    msg: TextDocument,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (!requestId) return;

    let chunkSize: number;
    let chunkOverlap: number;

    try {
      chunkSize = flowCtx.flow.parameter<number>("chunk-size");
    } catch {
      chunkSize = DEFAULT_CHUNK_SIZE;
    }

    try {
      chunkOverlap = flowCtx.flow.parameter<number>("chunk-overlap");
    } catch {
      chunkOverlap = DEFAULT_CHUNK_OVERLAP;
    }

    const text = msg.text;
    if (!text || text.trim().length === 0) {
      console.warn(`[ChunkingService] Empty text received for document ${msg.documentId}`);
      return;
    }

    const chunks = recursiveSplit(text, chunkSize, chunkOverlap);

    console.log(
      `[ChunkingService] Split document ${msg.documentId} into ${chunks.length} chunks (size=${chunkSize}, overlap=${chunkOverlap})`,
    );

    const outputProducer = flowCtx.flow.producer<Chunk>("output");

    for (const chunkText of chunks) {
      const chunk: Chunk = {
        metadata: msg.metadata,
        chunk: chunkText,
        documentId: msg.documentId,
      };

      await outputProducer.send(requestId, chunk);
    }
  }
}

export async function run(): Promise<void> {
  await ChunkingService.launch("chunking");
}
