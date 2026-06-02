/**
 * Request/response specification — declares a request/response client for a flow.
 *
 * Enables FlowProcessor handlers to make request/response calls to other services
 * (e.g., calling the prompt service or LLM from within a knowledge extraction handler).
 *
 * Python reference: trustgraph-base/trustgraph/base/prompt_client_spec.py
 */

import { Effect } from "effect";
import type { Spec } from "./types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import {
  RequestResponseFactory,
  type EffectRequestResponse,
} from "../messaging/runtime.js";

declare const RequestResponseSpecType: unique symbol;

export interface RequestResponseSpec<TReq, TRes> extends Spec {
  readonly [RequestResponseSpecType]?: {
    readonly request: TReq;
    readonly response: TRes;
  };
}

export function makeRequestResponseSpec<TReq, TRes>(
  name: string,
  requestTopicName: string,
  responseTopicName: string,
): RequestResponseSpec<TReq, TRes> {
  const addEffect = Effect.fn("RequestResponseSpec.addEffect")(function* (
    flow: Flow,
    definition: FlowDefinition,
  ) {
      const requestTopic = definition.topics?.[requestTopicName] ?? requestTopicName;
      const responseTopic = definition.topics?.[responseTopicName] ?? responseTopicName;
      const factory = yield* RequestResponseFactory;
      const requestor = yield* factory.make<TReq, TRes>({
        requestTopic,
        responseTopic,
        subscription: `${flow.processorId}-${flow.name}-${name}`,
      });
      flow.registerRequestor(name, requestor as EffectRequestResponse<unknown, unknown>);
  });

  return {
    name,
    addEffect,
    add: async (flow, pubsub, definition) => {
      await flow.runInCompatibilityScope(addEffect(flow, definition), pubsub);
    },
  };
}
