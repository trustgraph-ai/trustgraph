/**
 * Base embeddings service.
 *
 * Python reference: trustgraph-base/trustgraph/base/embeddings_service.py
 */

import { FlowProcessor } from "../processor/flow-processor.js";
import { ConsumerSpec } from "../spec/consumer-spec.js";
import { ProducerSpec } from "../spec/producer-spec.js";
import { ParameterSpec } from "../spec/parameter-spec.js";
import type { ProcessorConfig } from "../processor/async-processor.js";
import type { FlowContext } from "../messaging/consumer.js";
import type { EmbeddingsRequest, EmbeddingsResponse } from "../schema/messages.js";

export abstract class EmbeddingsService extends FlowProcessor {
  constructor(config: ProcessorConfig) {
    super(config);

    this.registerSpecification(
      new ConsumerSpec<EmbeddingsRequest>(
        "request",
        this.onRequest.bind(this),
      ),
    );
    this.registerSpecification(new ProducerSpec<EmbeddingsResponse>("response"));
    this.registerSpecification(new ParameterSpec("model"));
  }

  private async onRequest(
    msg: EmbeddingsRequest,
    properties: Record<string, string>,
    _flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (!requestId) return;

    try {
      const vectors = await this.onEmbeddings(msg.text, msg.model);
      void vectors; // Producer send would go here
    } catch (err) {
      console.error(`[EmbeddingsService] Error processing request:`, err);
    }
  }

  abstract onEmbeddings(texts: string[], model?: string): Promise<number[][]>;
}
