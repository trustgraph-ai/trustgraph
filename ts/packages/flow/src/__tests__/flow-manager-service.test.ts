import {Effect, SynchronizedRef} from "effect";
import {describe, expect, it} from "vitest";
import {
  topics,
  type BackendConsumer,
  type BackendProducer,
  type ConfigRequest,
  type ConfigResponse,
  type CreateConsumerOptions,
  type CreateProducerOptions,
  type FlowRequest,
  type FlowResponse,
  type Message,
  type PubSubBackend,
  type RequestResponse,
} from "@trustgraph/base";
import {FlowManagerError, makeFlowManagerService} from "../flow-manager/service.js";

class NoopPubSub implements PubSubBackend {
  readonly sentByTopic = new Map<string, Array<unknown>>();

  async createProducer<T>(options: CreateProducerOptions<T>): Promise<BackendProducer<T>> {
    return {
      send: async (message) => {
        const sent = this.sentByTopic.get(options.topic) ?? [];
        sent.push(message);
        this.sentByTopic.set(options.topic, sent);
      },
      flush: async () => undefined,
      close: async () => undefined,
    };
  }

  async createConsumer<T>(_options: CreateConsumerOptions): Promise<BackendConsumer<T>> {
    return {
      receive: async () => null,
      acknowledge: async () => undefined,
      negativeAcknowledge: async () => undefined,
      unsubscribe: async () => undefined,
      close: async () => undefined,
    };
  }

  async close(): Promise<void> {}
}

class RecordingConfigClient implements RequestResponse<ConfigRequest, ConfigResponse> {
  readonly requests: Array<ConfigRequest> = [];

  constructor(
    private readonly blueprints: Array<{readonly key: string; readonly value: unknown}> = [],
    private readonly flows: Array<{readonly key: string; readonly value: unknown}> = [],
    private readonly legacyFlows: Array<{readonly key: string; readonly value: unknown}> = [],
  ) {}

  async start(): Promise<void> {}

  async stop(): Promise<void> {}

  async request(request: ConfigRequest): Promise<ConfigResponse> {
    this.requests.push(request);
    if (request.operation !== "getvalues") return {};

    if (request.type === "flow-blueprint") {
      return {values: this.blueprints};
    }
    if (request.type === "flow") {
      return {values: this.flows};
    }
    if (request.type === "flows") {
      return {values: this.legacyFlows};
    }

    return {values: []};
  }
}

const makeService = (backend: PubSubBackend = new NoopPubSub()) =>
  makeFlowManagerService({
    id: "flow-manager-test",
    manageProcessSignals: false,
    pubsub: backend,
  });

const seedConfigClient = async (
  service: ReturnType<typeof makeFlowManagerService>,
  configClient: RecordingConfigClient,
) =>
  Effect.runPromise(
    SynchronizedRef.update(service.state, (state) => ({
      ...state,
      configClient,
    })),
  );

const seedResponseProducer = async (
  backend: NoopPubSub,
  service: ReturnType<typeof makeFlowManagerService>,
) => {
  const responseProducer = await backend.createProducer<FlowResponse>({
    topic: topics.flowResponse,
  });
  await Effect.runPromise(
    SynchronizedRef.update(service.state, (state) => ({
      ...state,
      responseProducer,
    })),
  );
};

describe("FlowManagerService operations", () => {
  it("uses tagged errors for invalid flow mutations", async () => {
    const service = makeService();

    const startError = await service.handleStartFlow({operation: "start-flow"})
      .catch((caught: unknown) => caught);
    const stopError = await service.handleStopFlow({operation: "stop-flow"})
      .catch((caught: unknown) => caught);

    expect(startError).toBeInstanceOf(FlowManagerError);
    expect(startError).toMatchObject({_tag: "FlowManagerError", operation: "start-flow"});
    expect(stopError).toBeInstanceOf(FlowManagerError);
    expect(stopError).toMatchObject({_tag: "FlowManagerError", operation: "stop-flow"});
  });

  it("mutates flow state through the ref and pushes config updates", async () => {
    const configClient = new RecordingConfigClient();
    const service = makeService();
    await seedConfigClient(service, configClient);

    await service.handleStartFlow({
      operation: "start-flow",
      "flow-id": "flow-a",
      description: "alpha",
      parameters: {limit: 3},
    });
    let state = await Effect.runPromise(SynchronizedRef.get(service.state));
    expect(state.flows.get("flow-a")).toMatchObject({
      id: "flow-a",
      blueprintName: "default",
      description: "alpha",
      parameters: {limit: 3},
      status: "running",
    });

    await service.handleStopFlow({
      operation: "stop-flow",
      "flow-id": "flow-a",
    });
    state = await Effect.runPromise(SynchronizedRef.get(service.state));

    expect(state.flows.has("flow-a")).toBe(false);
    expect(configClient.requests.map((request) => ({
      operation: request.operation,
      keys: request.keys,
    }))).toEqual([
      {operation: "put", keys: ["flows"]},
      {operation: "put", keys: ["flow"]},
      {operation: "delete", keys: ["flows", "flow-a"]},
      {operation: "delete", keys: ["flow", "flow-a"]},
      {operation: "put", keys: ["flows"]},
      {operation: "put", keys: ["flow"]},
    ]);
  });

  it("decodes valid blueprint config and skips invalid blueprint records", async () => {
    const configClient = new RecordingConfigClient([
      {
        key: "custom",
        value: "{\"description\":\"Custom\",\"topics\":{\"input\":\"topic.in\"},\"extra\":true}",
      },
      {
        key: "broken",
        value: "{\"description\":\"Missing topics\"}",
      },
    ]);
    const service = makeService();
    await seedConfigClient(service, configClient);

    await service.refreshBlueprintsFromConfig();
    const state = await Effect.runPromise(SynchronizedRef.get(service.state));

    expect(state.blueprints.get("custom")).toMatchObject({
      description: "Custom",
      topics: {input: "topic.in"},
      extra: true,
    });
    expect(state.blueprints.has("broken")).toBe(false);
    expect(state.blueprints.has("default")).toBe(true);
  });

  it("serializes duplicate starts through the ref-backed map", async () => {
    const configClient = new RecordingConfigClient();
    const service = makeService();
    await seedConfigClient(service, configClient);

    const results = await Promise.allSettled([
      service.handleStartFlow({operation: "start-flow", "flow-id": "flow-a"}),
      service.handleStartFlow({operation: "start-flow", "flow-id": "flow-a"}),
    ]);
    const state = await Effect.runPromise(SynchronizedRef.get(service.state));

    expect(state.flows.get("flow-a")).toMatchObject({id: "flow-a"});
    expect(results.filter((result) => result.status === "fulfilled")).toHaveLength(1);
    expect(results.filter((result) => result.status === "rejected")).toHaveLength(1);
  });

  it("sends flow-error responses from handleMessageEffect", async () => {
    const backend = new NoopPubSub();
    const configClient = new RecordingConfigClient();
    const service = makeService(backend);
    await seedConfigClient(service, configClient);
    await seedResponseProducer(backend, service);

    const message: Message<FlowRequest> = {
      value: () => ({operation: "start-flow"}),
      properties: () => ({id: "request-1"}),
    };

    await Effect.runPromise(service.handleMessageEffect(message));

    expect(backend.sentByTopic.get(topics.flowResponse)).toEqual([
      {
        error: {
          type: "flow-error",
          message: "Missing flow-id",
        },
      },
    ]);
  });
});
