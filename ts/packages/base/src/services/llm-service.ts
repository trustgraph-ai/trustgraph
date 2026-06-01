/**
 * Base LLM capability contract and message-bus adapter.
 *
 * Python reference: trustgraph-base/trustgraph/base/llm_service.py
 */

import { Context, Effect } from "effect";
import * as S from "effect/Schema";
import {
  errorMessage,
  type FlowResourceNotFoundError,
  type MessagingDeliveryError,
} from "../errors.js";
import type { FlowContext } from "../messaging/consumer.js";
import { FlowProcessor } from "../processor/flow-processor.js";
import type { ProcessorConfig } from "../processor/async-processor.js";
import type {
  TextCompletionRequest,
  TextCompletionResponse,
} from "../schema/messages.js";
import type { LlmChunk, LlmResult } from "../schema/primitives.js";
import { ConsumerSpec } from "../spec/consumer-spec.js";
import { ParameterSpec } from "../spec/parameter-spec.js";
import { ProducerSpec } from "../spec/producer-spec.js";
import type { Spec } from "../spec/types.js";

export class LlmServiceError extends S.TaggedErrorClass<LlmServiceError>()(
  "LlmServiceError",
  {
    message: S.String,
    operation: S.String,
  },
) {}

export interface LlmProvider {
  readonly generateContent: (
    system: string,
    prompt: string,
    model?: string,
    temperature?: number,
  ) => Promise<LlmResult>;
  readonly generateContentStream: (
    system: string,
    prompt: string,
    model?: string,
    temperature?: number,
  ) => AsyncGenerator<LlmChunk>;
  readonly supportsStreaming: () => boolean;
}

export interface LlmServiceShape {
  readonly generateContent: (
    system: string,
    prompt: string,
    model?: string,
    temperature?: number,
  ) => Effect.Effect<LlmResult, LlmServiceError>;
  readonly generateContentStream: (
    system: string,
    prompt: string,
    model?: string,
    temperature?: number,
  ) => AsyncGenerator<LlmChunk>;
  readonly supportsStreaming: () => boolean;
}

export class Llm extends Context.Service<Llm, LlmServiceShape>()(
  "@trustgraph/base/services/llm-service/Llm",
) {}

const llmServiceError = (operation: string, cause: unknown) =>
  new LlmServiceError({
    operation,
    message: errorMessage(cause),
  });

export const makeLlmServiceShape = (provider: LlmProvider): LlmServiceShape => ({
  generateContent: Effect.fn("Llm.generateContent")((
    system,
    prompt,
    model,
    temperature,
  ) =>
    Effect.tryPromise({
      try: () => provider.generateContent(system, prompt, model, temperature),
      catch: (cause) => llmServiceError("generate-content", cause),
    }),
  ),
  generateContentStream: (
    system,
    prompt,
    model,
    temperature,
  ) => provider.generateContentStream(system, prompt, model, temperature),
  supportsStreaming: () => provider.supportsStreaming(),
});

type LlmHandlerError =
  | FlowResourceNotFoundError
  | MessagingDeliveryError;

const resultToResponse = (result: LlmResult): TextCompletionResponse => ({
  response: result.text,
  model: result.model,
  inToken: result.inToken,
  outToken: result.outToken,
  endOfStream: true,
});

const chunkToResponse = (chunk: LlmChunk): TextCompletionResponse => ({
  response: chunk.text,
  model: chunk.model,
  ...(chunk.inToken !== null ? { inToken: chunk.inToken } : {}),
  ...(chunk.outToken !== null ? { outToken: chunk.outToken } : {}),
  endOfStream: chunk.isFinal,
});

const llmErrorResponse = (error: LlmServiceError): TextCompletionResponse => ({
  response: "",
  error: {
    type: "llm-error",
    message: error.message,
  },
  endOfStream: true,
});

const sendStreamingResponse = Effect.fn("LlmService.sendStreamingResponse")(function* (
  llm: LlmServiceShape,
  requestId: string,
  msg: TextCompletionRequest,
  responseProducer: {
    readonly send: (
      id: string,
      message: TextCompletionResponse,
    ) => Effect.Effect<void, MessagingDeliveryError>;
  },
) {
  const context = yield* Effect.context<never>();
  yield* Effect.tryPromise({
    try: async () => {
      for await (const chunk of llm.generateContentStream(
        msg.system,
        msg.prompt,
        msg.model,
        msg.temperature,
      )) {
        await Effect.runPromiseWith(context)(
          responseProducer.send(requestId, chunkToResponse(chunk)),
        );
      }
    },
    catch: (cause) => llmServiceError("generate-content-stream", cause),
  });
});

const onLlmRequest = Effect.fn("LlmService.onRequest")(function* (
  msg: TextCompletionRequest,
  properties: Record<string, string>,
  flowCtx: FlowContext<Llm>,
): Effect.fn.Return<void, LlmHandlerError, Llm> {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const responseProducer = yield* flowCtx.flow.producerEffect<TextCompletionResponse>(
    "text-completion-response",
  );
  const llm = yield* Llm;

  if (msg.streaming === true && llm.supportsStreaming()) {
    yield* sendStreamingResponse(llm, requestId, msg, responseProducer).pipe(
      Effect.catch((error) =>
        Effect.logError("[LlmService] Error processing streaming request", {
          error: error.message,
          operation: error.operation,
        }).pipe(
          Effect.flatMap(() =>
            responseProducer.send(requestId, llmErrorResponse(error)),
          ),
        ),
      ),
    );
    return;
  }

  const response = yield* llm.generateContent(
    msg.system,
    msg.prompt,
    msg.model,
    msg.temperature,
  ).pipe(
    Effect.map(resultToResponse),
    Effect.catch((error) =>
      Effect.logError("[LlmService] Error processing request", {
        error: error.message,
        operation: error.operation,
      }).pipe(
        Effect.as(llmErrorResponse(error)),
      ),
    ),
  );

  yield* responseProducer.send(requestId, response);
});

export const makeLlmSpecs = (): ReadonlyArray<Spec<Llm>> => [
  new ConsumerSpec<TextCompletionRequest, LlmHandlerError, Llm>(
    "text-completion-request",
    onLlmRequest,
  ),
  new ProducerSpec<TextCompletionResponse>("text-completion-response"),
  new ParameterSpec("model"),
  new ParameterSpec("temperature"),
];

export abstract class LlmService extends FlowProcessor<Llm> implements LlmProvider {
  protected constructor(config: ProcessorConfig) {
    super(config);

    for (const spec of makeLlmSpecs()) {
      this.registerSpecification(spec);
    }
  }

  override startEffect() {
    return super.startEffect().pipe(
      Effect.provideService(Llm, Llm.of(makeLlmServiceShape(this))),
    );
  }

  abstract generateContent(
    system: string,
    prompt: string,
    model?: string,
    temperature?: number,
  ): Promise<LlmResult>;

  abstract generateContentStream(
    system: string,
    prompt: string,
    model?: string,
    temperature?: number,
  ): AsyncGenerator<LlmChunk>;

  supportsStreaming(): boolean {
    return false;
  }
}
