/**
 * Effect Config contracts for messaging runtime behavior.
 */

import { Config, Effect } from "effect";

export interface MessagingRuntimeConfig {
  readonly consumerReceiveTimeoutMs: number;
  readonly consumerErrorBackoffMs: number;
  readonly rateLimitRetryMs: number;
  readonly requestTimeoutMs: number;
}

export const defaultMessagingRuntimeConfig: MessagingRuntimeConfig = {
  consumerReceiveTimeoutMs: 2_000,
  consumerErrorBackoffMs: 1_000,
  rateLimitRetryMs: 10_000,
  requestTimeoutMs: 300_000,
};

export const loadMessagingRuntimeConfig = Effect.fn("loadMessagingRuntimeConfig")(function* () {
  const consumerReceiveTimeoutMs = yield* Config.number("TG_CONSUMER_RECEIVE_TIMEOUT_MS").pipe(
    Config.withDefault(defaultMessagingRuntimeConfig.consumerReceiveTimeoutMs),
  );
  const consumerErrorBackoffMs = yield* Config.number("TG_CONSUMER_ERROR_BACKOFF_MS").pipe(
    Config.withDefault(defaultMessagingRuntimeConfig.consumerErrorBackoffMs),
  );
  const rateLimitRetryMs = yield* Config.number("TG_RATE_LIMIT_RETRY_MS").pipe(
    Config.withDefault(defaultMessagingRuntimeConfig.rateLimitRetryMs),
  );
  const requestTimeoutMs = yield* Config.number("TG_REQUEST_TIMEOUT_MS").pipe(
    Config.withDefault(defaultMessagingRuntimeConfig.requestTimeoutMs),
  );

  return {
    consumerReceiveTimeoutMs,
    consumerErrorBackoffMs,
    rateLimitRetryMs,
    requestTimeoutMs,
  } satisfies MessagingRuntimeConfig;
});
