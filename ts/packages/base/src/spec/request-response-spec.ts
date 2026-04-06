/**
 * Request/response specification — declares a request/response client for a flow.
 *
 * Enables FlowProcessor handlers to make request/response calls to other services
 * (e.g., calling the prompt service or LLM from within a knowledge extraction handler).
 *
 * Python reference: trustgraph-base/trustgraph/base/prompt_client_spec.py
 */

import type { Spec } from "./types.js";
import type { PubSubBackend } from "../backend/types.js";
import type { Flow, FlowDefinition } from "../processor/flow.js";
import { RequestResponse } from "../messaging/request-response.js";

export class RequestResponseSpec<TReq, TRes> implements Spec {
  constructor(
    public readonly name: string,
    private readonly requestTopicName: string,
    private readonly responseTopicName: string,
  ) {}

  async add(flow: Flow, pubsub: PubSubBackend, definition: FlowDefinition): Promise<void> {
    const requestTopic = definition.topics?.[this.requestTopicName] ?? this.requestTopicName;
    const responseTopic = definition.topics?.[this.responseTopicName] ?? this.responseTopicName;

    const rr = new RequestResponse<TReq, TRes>({
      pubsub,
      requestTopic,
      responseTopic,
      subscription: `${flow.processorId}-${flow.name}-${this.name}`,
    });
    await rr.start();

    flow.registerRequestor(this.name, rr as RequestResponse<unknown, unknown>);
  }
}
