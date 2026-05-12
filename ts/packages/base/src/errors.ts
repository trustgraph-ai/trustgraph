/**
 * Typed errors and wire-error translation helpers.
 *
 * Python reference: trustgraph-base/trustgraph/exceptions.py
 */

import * as S from "effect/Schema";
import type { TgError } from "./schema/primitives.js";

export class TooManyRequestsError extends S.TaggedErrorClass<TooManyRequestsError>()(
  "TooManyRequestsError",
  {
    message: S.String,
  },
) {}

export class LlmError extends S.TaggedErrorClass<LlmError>()(
  "LlmError",
  {
    message: S.String,
    errorType: S.String,
  },
) {}

export class EmbeddingsError extends S.TaggedErrorClass<EmbeddingsError>()(
  "EmbeddingsError",
  {
    message: S.String,
    operation: S.String,
    provider: S.optionalKey(S.String),
  },
) {}

export class ParseError extends S.TaggedErrorClass<ParseError>()(
  "ParseError",
  {
    message: S.String,
  },
) {}

export class RuntimeConfigError extends S.TaggedErrorClass<RuntimeConfigError>()(
  "RuntimeConfigError",
  {
    message: S.String,
    key: S.optionalKey(S.String),
  },
) {}

export class WireDecodeError extends S.TaggedErrorClass<WireDecodeError>()(
  "WireDecodeError",
  {
    message: S.String,
    service: S.optionalKey(S.String),
  },
) {}

export class PubSubError extends S.TaggedErrorClass<PubSubError>()(
  "PubSubError",
  {
    message: S.String,
    operation: S.String,
  },
) {}

export class ProcessorLifecycleError extends S.TaggedErrorClass<ProcessorLifecycleError>()(
  "ProcessorLifecycleError",
  {
    message: S.String,
    operation: S.String,
    processorId: S.String,
  },
) {}

export class MessagingLifecycleError extends S.TaggedErrorClass<MessagingLifecycleError>()(
  "MessagingLifecycleError",
  {
    message: S.String,
    operation: S.String,
    resource: S.String,
  },
) {}

export class MessagingDeliveryError extends S.TaggedErrorClass<MessagingDeliveryError>()(
  "MessagingDeliveryError",
  {
    message: S.String,
    operation: S.String,
    topic: S.String,
  },
) {}

export class MessagingDecodeError extends S.TaggedErrorClass<MessagingDecodeError>()(
  "MessagingDecodeError",
  {
    message: S.String,
    operation: S.String,
    topic: S.optionalKey(S.String),
  },
) {}

export class MessagingTimeoutError extends S.TaggedErrorClass<MessagingTimeoutError>()(
  "MessagingTimeoutError",
  {
    message: S.String,
    operation: S.String,
    timeoutMs: S.Number,
  },
) {}

export class MessagingHandlerError extends S.TaggedErrorClass<MessagingHandlerError>()(
  "MessagingHandlerError",
  {
    message: S.String,
    topic: S.String,
    subscription: S.String,
  },
) {}

export class FlowRuntimeError extends S.TaggedErrorClass<FlowRuntimeError>()(
  "FlowRuntimeError",
  {
    message: S.String,
    flowName: S.String,
    operation: S.String,
  },
) {}

export class FlowResourceNotFoundError extends S.TaggedErrorClass<FlowResourceNotFoundError>()(
  "FlowResourceNotFoundError",
  {
    message: S.String,
    flowName: S.String,
    resourceType: S.Union([
      S.Literal("producer"),
      S.Literal("consumer"),
      S.Literal("requestor"),
      S.Literal("parameter"),
    ]),
    resourceName: S.String,
  },
) {}

export type TrustGraphError =
  | TooManyRequestsError
  | LlmError
  | EmbeddingsError
  | ParseError
  | RuntimeConfigError
  | WireDecodeError
  | PubSubError
  | ProcessorLifecycleError
  | MessagingLifecycleError
  | MessagingDeliveryError
  | MessagingDecodeError
  | MessagingTimeoutError
  | MessagingHandlerError
  | FlowRuntimeError
  | FlowResourceNotFoundError;

export type MessagingRuntimeError =
  | PubSubError
  | MessagingLifecycleError
  | MessagingDeliveryError
  | MessagingDecodeError
  | MessagingTimeoutError
  | MessagingHandlerError
  | FlowRuntimeError
  | FlowResourceNotFoundError;

export function tooManyRequestsError(message = "Rate limit exceeded"): TooManyRequestsError {
  return new TooManyRequestsError({ message });
}

export function llmError(message: string, errorType = "llm-error"): LlmError {
  return new LlmError({ message, errorType });
}

export function embeddingsError(
  operation: string,
  error: unknown,
  provider?: string,
): EmbeddingsError {
  return new EmbeddingsError({
    operation,
    message: errorMessage(error),
    ...(provider === undefined ? {} : { provider }),
  });
}

export function parseError(message: string): ParseError {
  return new ParseError({ message });
}

export function pubSubError(operation: string, error: unknown): PubSubError {
  return new PubSubError({ operation, message: errorMessage(error) });
}

export function processorLifecycleError(
  processorId: string,
  operation: string,
  error: unknown,
): ProcessorLifecycleError {
  return new ProcessorLifecycleError({
    processorId,
    operation,
    message: errorMessage(error),
  });
}

export function messagingLifecycleError(
  resource: string,
  operation: string,
  error: unknown,
): MessagingLifecycleError {
  return new MessagingLifecycleError({
    resource,
    operation,
    message: errorMessage(error),
  });
}

export function messagingDeliveryError(
  topic: string,
  operation: string,
  error: unknown,
): MessagingDeliveryError {
  return new MessagingDeliveryError({
    topic,
    operation,
    message: errorMessage(error),
  });
}

export function messagingDecodeError(
  operation: string,
  error: unknown,
  topic?: string,
): MessagingDecodeError {
  return new MessagingDecodeError({
    operation,
    message: errorMessage(error),
    ...(topic === undefined ? {} : { topic }),
  });
}

export function messagingTimeoutError(
  operation: string,
  timeoutMs: number,
): MessagingTimeoutError {
  return new MessagingTimeoutError({
    operation,
    timeoutMs,
    message: `${operation} timed out after ${timeoutMs}ms`,
  });
}

export function messagingHandlerError(
  topic: string,
  subscription: string,
  error: unknown,
): MessagingHandlerError {
  return new MessagingHandlerError({
    topic,
    subscription,
    message: errorMessage(error),
  });
}

export function flowRuntimeError(
  flowName: string,
  operation: string,
  error: unknown,
): FlowRuntimeError {
  return new FlowRuntimeError({
    flowName,
    operation,
    message: errorMessage(error),
  });
}

export function flowResourceNotFoundError(
  flowName: string,
  resourceType: FlowResourceNotFoundError["resourceType"],
  resourceName: string,
): FlowResourceNotFoundError {
  return new FlowResourceNotFoundError({
    flowName,
    resourceType,
    resourceName,
    message: `${resourceType} "${resourceName}" not found in flow "${flowName}"`,
  });
}

export function errorMessage(error: unknown): string {
  if (typeof error === "object" && error !== null && "message" in error) {
    const message = (error as { message?: unknown }).message;
    if (typeof message === "string") return message;
  }
  return String(error);
}

export function toTgError(error: unknown, fallbackType = "internal"): TgError {
  if (typeof error === "object" && error !== null && "_tag" in error) {
    const tag = (error as { _tag?: unknown })._tag;
    if (typeof tag === "string") {
      return { type: tag, message: errorMessage(error) };
    }
  }
  return { type: fallbackType, message: errorMessage(error) };
}
