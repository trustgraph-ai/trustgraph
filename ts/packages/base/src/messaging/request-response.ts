/**
 * Request/response pattern over pub/sub.
 *
 * Sends a request with a unique ID, subscribes for matching responses.
 * Supports streaming (multiple responses per request) via a recipient callback.
 *
 * Python reference: trustgraph-base/trustgraph/base/request_response_spec.py
 */

import { Effect, Exit, Scope } from "effect";
import type { PubSubBackend } from "../backend/types.js";
import { PubSub } from "../backend/pubsub.js";
import { messagingDeliveryError, messagingLifecycleError } from "../errors.js";
import { loadMessagingRuntimeConfig } from "../runtime/index.ts";
import { makeEffectRequestResponseFromPubSub, type EffectRequestResponse } from "./runtime.js";

export interface RequestResponseOptions {
  pubsub: PubSubBackend;
  requestTopic: string;
  responseTopic: string;
  subscription: string;
}

export interface RequestResponse<TReq, TRes> {
  readonly start: () => Promise<void>;
  readonly stop: () => Promise<void>;
  readonly request: (
    request: TReq,
    options?: {
      timeoutMs?: number;
      recipient?: (response: TRes) => Promise<boolean>;
    },
  ) => Promise<TRes>;
}

interface RequestResponseRuntime<TReq, TRes> {
  readonly scope: Scope.Closeable;
  readonly requestor: EffectRequestResponse<TReq, TRes>;
}

export function makeRequestResponse<TReq, TRes>(
  options: RequestResponseOptions,
): RequestResponse<TReq, TRes> {
  let runtime: RequestResponseRuntime<TReq, TRes> | null = null;

  return {
    start: () =>
      runtime !== null
        ? Promise.resolve()
        : Effect.runPromise(
            Effect.gen(function* () {
              const scope = yield* Scope.make();
              const startRuntime = Effect.gen(function* () {
                const config = yield* loadMessagingRuntimeConfig();
                const requestor = yield* makeEffectRequestResponseFromPubSub<TReq, TRes>(
                  PubSub.fromBackend(options.pubsub),
                  config,
                  {
                    requestTopic: options.requestTopic,
                    responseTopic: options.responseTopic,
                    subscription: options.subscription,
                  },
                ).pipe(Scope.provide(scope));

                runtime = { scope, requestor };
              });

              yield* startRuntime.pipe(
                Effect.catch((error) =>
                  Scope.close(scope, Exit.fail(error)).pipe(
                    Effect.flatMap(() => Effect.fail(error)),
                  ),
                ),
              );
            }),
          ),
    stop: () => {
      const current = runtime;
      runtime = null;
      return current === null
        ? Promise.resolve()
        : Effect.runPromise(Scope.close(current.scope, Exit.void));
    },
    /**
     * Send a request and wait for responses.
     *
     * @param request - The request payload
     * @param requestOptions.timeoutMs - Total timeout in milliseconds (default: 300s)
     * @param requestOptions.recipient - Optional callback for streaming responses.
     *   Return `true` to indicate the final response has been received.
     *   If omitted, returns the first response.
     */
    request: (request, requestOptions) => {
      const current = runtime;
      if (current === null) {
        return Effect.runPromise(
          Effect.fail(
            messagingLifecycleError(
              `${options.requestTopic}:${options.responseTopic}`,
              "request",
              "RequestResponse not started",
            ),
          ),
        );
      }

      const timeoutMs = requestOptions?.timeoutMs ?? 300_000;
      const recipient = requestOptions?.recipient;

      return Effect.runPromise(
        current.requestor.request(request, {
          timeoutMs,
          ...(recipient === undefined
            ? {}
            : {
                recipient: (response) =>
                  Effect.tryPromise({
                    try: () => recipient(response),
                    catch: (error) => messagingDeliveryError(options.responseTopic, "recipient", error),
                  }),
              }),
        }),
      );
    },
  };
}
