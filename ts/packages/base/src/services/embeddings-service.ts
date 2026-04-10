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
  protected constructor(config: ProcessorConfig) {
    super(config);

    this.registerSpecification(
      new ConsumerSpec<EmbeddingsRequest>(
        "embeddings-request",
        this.onRequest.bind(this),
      ),
    );
    this.registerSpecification(new ProducerSpec<EmbeddingsResponse>("embeddings-response"));
    this.registerSpecification(new ParameterSpec("model"));
  }

  private async onRequest(
    msg: EmbeddingsRequest,
    properties: Record<string, string>,
    flowCtx: FlowContext,
  ): Promise<void> {
    const requestId = properties.id;
    if (!requestId) return;

    const responseProducer = flowCtx.flow.producer<EmbeddingsResponse>("embeddings-response");

    try {
      const vectors = await this.onEmbeddings(msg.text, msg.model);
      await responseProducer.send(requestId, { vectors });
    } catch (err) {
      console.error(`[EmbeddingsService] Error processing request:`, err);

      const message = err instanceof Error ? err.message : String(err);
      await responseProducer.send(requestId, {
        vectors: [],
        error: { type: "embeddings-error", message },
      });
    }
  }

  abstract onEmbeddings(texts: string[], model?: string): Promise<number[][]>;
}
