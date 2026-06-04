/**
 * Request/response specification — declares a request/response client for a flow.
 *
 * Enables FlowProcessor handlers to make request/response calls to other services
 * (e.g., calling the prompt service or LLM from within a knowledge extraction handler).
 *
 * Python reference: trustgraph-base/trustgraph/base/prompt_client_spec.py
 */

import { Effect, type Context } from "effect";
import type { SpecRuntimeRequirements } from "./types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import type { PubSubBackend } from "../backend/types.js";
import {
  flowResourceNotFoundError,
  type FlowResourceNotFoundError,
  type PubSubError,
} from "../errors.js";
import {
  type EffectRequestResponse,
  RequestResponseFactory,
} from "../messaging/runtime.js";

declare const RequestResponseSpecType: unique symbol;

export interface RequestResponseSpec<TReq, TRes> {
  readonly [RequestResponseSpecType]?: {
    readonly request: TReq;
    readonly response: TRes;
  };
  readonly name: string;
  readonly addEffect: <Requirements = never>(
    flow: Flow<Requirements>,
    definition: FlowDefinition,
  ) => Effect.Effect<void, PubSubError, SpecRuntimeRequirements | Requirements>;
  readonly add: <Requirements = never>(
    flow: Flow<Requirements>,
    pubsub: PubSubBackend,
    definition: FlowDefinition,
    context: Context.Context<Requirements>,
  ) => Promise<void>;
  readonly requestorEffect: <Requirements = never>(
    flow: Flow<Requirements>,
  ) => Effect.Effect<EffectRequestResponse<TReq, TRes>, FlowResourceNotFoundError>;
}

export function makeRequestResponseSpec<TReq, TRes>(
  name: string,
  requestTopicName: string,
  responseTopicName: string,
): RequestResponseSpec<TReq, TRes> {
  const requestors = new WeakMap<object, EffectRequestResponse<TReq, TRes>>();

  const registerRequestor = <Requirements>(
    flow: Flow<Requirements>,
    requestor: EffectRequestResponse<TReq, TRes>,
  ) =>
    Effect.sync(() => {
      requestors.set(flow, requestor);
    });

  const unregisterRequestor = <Requirements>(
    flow: Flow<Requirements>,
    requestor: EffectRequestResponse<TReq, TRes>,
  ) =>
    Effect.sync(() => {
      if (requestors.get(flow) === requestor) {
        requestors.delete(flow);
      }
    });

  const requestorEffect = <Requirements>(
    flow: Flow<Requirements>,
  ): Effect.Effect<EffectRequestResponse<TReq, TRes>, FlowResourceNotFoundError> => {
    const requestor = requestors.get(flow);
    return requestor === undefined
      ? Effect.fail(flowResourceNotFoundError(flow.name, "requestor", name))
      : Effect.succeed(requestor);
  };

  const addEffect = Effect.fn("RequestResponseSpec.addEffect")(function* <Requirements = never>(
    flow: Flow<Requirements>,
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
      flow.registerRequestor(name, requestor);
      yield* registerRequestor(flow, requestor);
      yield* Effect.addFinalizer(() => unregisterRequestor(flow, requestor));
  });

  return {
    name,
    requestorEffect,
    addEffect,
    add: (flow, pubsub, definition, context) =>
      flow.runInCompatibilityScope(addEffect(flow, definition), pubsub, context),
  };
}
