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
import type { PubSubBackend } from "../backend/types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import {
  RequestResponseFactory,
  type EffectRequestResponse,
} from "../messaging/runtime.js";

export class RequestResponseSpec<TReq, TRes> implements Spec {
  public readonly name: string;
  private readonly requestTopicName: string;
  private readonly responseTopicName: string;

  constructor(
    name: string,
    requestTopicName: string,
    responseTopicName: string,
  ) {
    this.name = name;
    this.requestTopicName = requestTopicName;
    this.responseTopicName = responseTopicName;
  }

  addEffect(flow: Flow, definition: FlowDefinition) {
    const spec = this;
    return Effect.gen(function* () {
      const requestTopic = definition.topics?.[spec.requestTopicName] ?? spec.requestTopicName;
      const responseTopic = definition.topics?.[spec.responseTopicName] ?? spec.responseTopicName;
      const factory = yield* RequestResponseFactory;
      const requestor = yield* factory.make<TReq, TRes>({
        requestTopic,
        responseTopic,
        subscription: `${flow.processorId}-${flow.name}-${spec.name}`,
      });
      flow.registerRequestor(spec.name, requestor as EffectRequestResponse<unknown, unknown>);
    });
  }

  async add(flow: Flow, pubsub: PubSubBackend, definition: FlowDefinition): Promise<void> {
    await flow.runInCompatibilityScope(this.addEffect(flow, definition), pubsub);
  }
}
