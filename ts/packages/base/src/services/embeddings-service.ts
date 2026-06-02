/**
 * Embeddings capability contract and message-bus adapter.
 *
 * Python reference: trustgraph-base/trustgraph/base/embeddings_service.py
 */

import { Context, Effect } from "effect";
import {
  errorMessage,
  type EmbeddingsError,
  type FlowResourceNotFoundError,
  type MessagingDeliveryError,
} from "../errors.js";
import type { FlowContext } from "../messaging/consumer.js";
import { makeFlowProcessor } from "../processor/index.ts";
import type { FlowProcessorRuntime, ProcessorConfig } from "../processor/index.ts";
import type { EmbeddingsRequest, EmbeddingsResponse } from "../schema/messages.js";
import { makeConsumerSpec } from "../spec/index.ts";
import { makeParameterSpec } from "../spec/index.ts";
import { makeProducerSpec } from "../spec/index.ts";
import type { Spec } from "../spec/types.js";

export interface EmbeddingsServiceShape {
  readonly embed: (
    texts: ReadonlyArray<string>,
    model?: string,
  ) => Effect.Effect<number[][], EmbeddingsError>;
}

export class Embeddings extends Context.Service<Embeddings, EmbeddingsServiceShape>()(
  "@trustgraph/base/services/embeddings-service/Embeddings",
) {}

const onEmbeddingsRequest = Effect.fn("EmbeddingsService.onRequest")(function* (
  msg: EmbeddingsRequest,
  properties: Record<string, string>,
  flowCtx: FlowContext<Embeddings>,
): Effect.fn.Return<void, FlowResourceNotFoundError | MessagingDeliveryError, Embeddings> {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) {
    return;
  }

  const responseProducer = yield* flowCtx.flow.producerEffect<EmbeddingsResponse>("embeddings-response");
  const embeddings = yield* Embeddings;
  const response = yield* embeddings.embed(msg.text, msg.model).pipe(
    Effect.map((vectors) => ({ vectors }) satisfies EmbeddingsResponse),
    Effect.catch((error) =>
      Effect.logError("[EmbeddingsService] Error processing request", {
        error: errorMessage(error),
        operation: error.operation,
        provider: error.provider ?? "unknown",
      }).pipe(
        Effect.as({
          vectors: [],
          error: {
            type: "embeddings-error",
            message: errorMessage(error),
          },
        } satisfies EmbeddingsResponse),
      ),
    ),
  );

  yield* responseProducer.send(requestId, response);
});

export const makeEmbeddingsSpecs = (): ReadonlyArray<Spec<Embeddings>> => [
  makeConsumerSpec<EmbeddingsRequest, FlowResourceNotFoundError | MessagingDeliveryError, Embeddings>(
    "embeddings-request",
    onEmbeddingsRequest,
  ),
  makeProducerSpec<EmbeddingsResponse>("embeddings-response"),
  makeParameterSpec("model"),
];

export type EmbeddingsService = FlowProcessorRuntime<Embeddings>;

export function makeEmbeddingsService(
  config: ProcessorConfig,
  embeddings?: EmbeddingsServiceShape,
): EmbeddingsService {
  return makeFlowProcessor(config, {
    specifications: makeEmbeddingsSpecs(),
    ...(embeddings === undefined
      ? {}
      : {
          provide: (effect) =>
            effect.pipe(
              Effect.provideService(Embeddings, Embeddings.of(embeddings)),
            ),
        }),
  });
}

export const EmbeddingsService = makeEmbeddingsService;
