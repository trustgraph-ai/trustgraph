/**
 * Effect Config contracts for messaging runtime behavior.
 */

import { Config, Duration, Effect } from "effect";

export interface MessagingRuntimeConfig {
  readonly consumerReceiveTimeout: Duration.Duration;
  readonly consumerErrorBackoff: Duration.Duration;
  readonly rateLimitRetry: Duration.Duration;
  readonly rateLimitTimeout: Duration.Duration;
  readonly requestTimeout: Duration.Duration;
}

export const defaultMessagingRuntimeConfig: MessagingRuntimeConfig = {
  consumerReceiveTimeout: Duration.millis(2_000),
  consumerErrorBackoff: Duration.millis(1_000),
  rateLimitRetry: Duration.millis(10_000),
  rateLimitTimeout: Duration.millis(7_200_000),
  requestTimeout: Duration.millis(300_000),
};

const durationConfig = (name: string, defaultValue: Duration.Duration) =>
  Config.duration(name).pipe(
    Config.orElse(() => Config.number(name).pipe(Config.map(Duration.millis))),
    Config.withDefault(defaultValue),
  );

export const loadMessagingRuntimeConfig = Effect.fn("loadMessagingRuntimeConfig")(function* () {
  const consumerReceiveTimeout = yield* durationConfig(
    "TG_CONSUMER_RECEIVE_TIMEOUT_MS",
    defaultMessagingRuntimeConfig.consumerReceiveTimeout,
  );
  const consumerErrorBackoff = yield* durationConfig(
    "TG_CONSUMER_ERROR_BACKOFF_MS",
    defaultMessagingRuntimeConfig.consumerErrorBackoff,
  );
  const rateLimitRetry = yield* durationConfig(
    "TG_RATE_LIMIT_RETRY_MS",
    defaultMessagingRuntimeConfig.rateLimitRetry,
  );
  const rateLimitTimeout = yield* durationConfig(
    "TG_RATE_LIMIT_TIMEOUT_MS",
    defaultMessagingRuntimeConfig.rateLimitTimeout,
  );
  const requestTimeout = yield* durationConfig(
    "TG_REQUEST_TIMEOUT_MS",
    defaultMessagingRuntimeConfig.requestTimeout,
  );

  return {
    consumerReceiveTimeout,
    consumerErrorBackoff,
    rateLimitRetry,
    rateLimitTimeout,
    requestTimeout,
  } satisfies MessagingRuntimeConfig;
});
