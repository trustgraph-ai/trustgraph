/**
 * Base LLM capability contract and message-bus adapter.
 *
 * Python reference: trustgraph-base/trustgraph/base/llm_service.py
 */

import { Context, Effect, Stream } from "effect";
import * as S from "effect/Schema";
import type {
  FlowResourceNotFoundError,
  MessagingDeliveryError,
} from "../errors.js";
import {
  errorMessage,
} from "../errors.js";
import type { FlowContext } from "../messaging/consumer.js";
import { makeFlowProcessor } from "../processor/index.ts";
import type { FlowProcessorRuntime, ProcessorConfig } from "../processor/index.ts";
import type {
  TextCompletionRequest,
  TextCompletionResponse,
} from "../schema/messages.js";
import type { LlmChunk, LlmResult } from "../schema/index.ts";
import { makeConsumerSpec } from "../spec/index.ts";
import { makeParameterSpec } from "../spec/index.ts";
import { makeProducerSpec } from "../spec/index.ts";
import type { Spec } from "../spec/types.js";

export class LlmServiceError extends S.TaggedErrorClass<LlmServiceError>()(
  "LlmServiceError",
  {
    message: S.String,
    operation: S.String,
  },
) {}

export interface LlmProvider<ProviderError = never> {
  readonly generateContent: (
    system: string,
    prompt: string,
    model?: string,
    temperature?: number,
  ) => Effect.Effect<LlmResult, ProviderError>;
  readonly generateContentStream: (
    system: string,
    prompt: string,
    model?: string,
    temperature?: number,
  ) => Stream.Stream<LlmChunk, ProviderError>;
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
  ) => Stream.Stream<LlmChunk, LlmServiceError>;
  readonly supportsStreaming: () => boolean;
}

export class Llm extends Context.Service<Llm, LlmServiceShape>()(
  "@trustgraph/base/services/llm-service/Llm",
) {}

const llmServiceError = (operation: string, cause: unknown) =>
  LlmServiceError.make({
    operation,
    message: errorMessage(cause),
  });

export const makeLlmServiceShape = <ProviderError>(
  provider: LlmProvider<ProviderError>,
): LlmServiceShape => ({
  generateContent: Effect.fn("Llm.generateContent")((
    system,
    prompt,
    model,
    temperature,
  ) =>
    provider.generateContent(system, prompt, model, temperature).pipe(
      Effect.mapError((cause) => llmServiceError("generate-content", cause)),
    ),
  ),
  generateContentStream: (
    system,
    prompt,
    model,
    temperature,
  ) =>
    provider.generateContentStream(system, prompt, model, temperature).pipe(
      Stream.mapError((cause) => llmServiceError("generate-content-stream", cause)),
    ),
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

const TextCompletionResponseProducer = makeProducerSpec<TextCompletionResponse>("text-completion-response");

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
  yield* llm.generateContentStream(
    msg.system,
    msg.prompt,
    msg.model,
    msg.temperature,
  ).pipe(
    Stream.runForEach((chunk) =>
      responseProducer.send(requestId, chunkToResponse(chunk)),
    ),
  );
});

const onLlmRequest = Effect.fn("LlmService.onRequest")(function* (
  msg: TextCompletionRequest,
  properties: Record<string, string>,
  flowCtx: FlowContext<Llm>,
): Effect.fn.Return<void, LlmHandlerError, Llm> {
  const requestId = properties.id;
  if (requestId === undefined || requestId.length === 0) return;

  const responseProducer = yield* flowCtx.flow.producerEffect(TextCompletionResponseProducer);
  const llm = yield* Llm;

  if (msg.streaming === true && llm.supportsStreaming()) {
    yield* sendStreamingResponse(llm, requestId, msg, responseProducer).pipe(
      Effect.catchTags({
        LlmServiceError: (error) =>
          Effect.logError("[LlmService] Error processing streaming request", {
            error: error.message,
            operation: error.operation,
          }).pipe(
            Effect.flatMap(() =>
              responseProducer.send(requestId, llmErrorResponse(error)),
            ),
          ),
        MessagingDeliveryError: (error) =>
          Effect.logError("[LlmService] Error sending streaming response", {
            error: error.message,
            operation: error.operation,
          }),
      }),
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
  makeConsumerSpec<TextCompletionRequest, LlmHandlerError, Llm>(
    "text-completion-request",
    onLlmRequest,
  ),
  TextCompletionResponseProducer,
  makeParameterSpec("model"),
  makeParameterSpec("temperature"),
];

export type LlmService<ProviderError = never> =
  & FlowProcessorRuntime<Llm>
  & LlmProvider<ProviderError>;

export function makeLlmService<ProviderError>(
  config: ProcessorConfig,
  provider: LlmProvider<ProviderError>,
): LlmService<ProviderError> {
  const service = makeFlowProcessor(config, {
    specifications: makeLlmSpecs(),
    provide: (effect) =>
      effect.pipe(
        Effect.provideService(Llm, Llm.of(makeLlmServiceShape(provider))),
      ),
  });
  return Object.assign(service, provider);
}

export const LlmService = makeLlmService;
