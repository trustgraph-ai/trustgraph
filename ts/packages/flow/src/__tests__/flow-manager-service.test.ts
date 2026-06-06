import {Effect, HashMap, Option, SynchronizedRef} from "effect";
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

  createProducer<T>(options: CreateProducerOptions<T>): Effect.Effect<BackendProducer<T>> {
    return Effect.succeed({
      send: (message) => Effect.sync(() => {
        const sent = this.sentByTopic.get(options.topic) ?? [];
        sent.push(message);
        this.sentByTopic.set(options.topic, sent);
      }),
      flush: Effect.void,
      close: Effect.void,
    });
  }

  createConsumer<T>(_options: CreateConsumerOptions): Effect.Effect<BackendConsumer<T>> {
    return Effect.succeed({
      receive: () => Effect.succeed(null),
      acknowledge: () => Effect.void,
      negativeAcknowledge: () => Effect.void,
      unsubscribe: Effect.void,
      close: Effect.void,
    });
  }

  readonly close: Effect.Effect<void> = Effect.void;
}

class RecordingConfigClient implements RequestResponse<ConfigRequest, ConfigResponse> {
  readonly requests: Array<ConfigRequest> = [];

  constructor(
    private readonly blueprints: Array<{readonly key: string; readonly value: unknown}> = [],
    private readonly flows: Array<{readonly key: string; readonly value: unknown}> = [],
    private readonly legacyFlows: Array<{readonly key: string; readonly value: unknown}> = [],
  ) {}

  readonly start: Effect.Effect<void> = Effect.void;

  readonly stop: Effect.Effect<void> = Effect.void;

  request(request: ConfigRequest): Effect.Effect<ConfigResponse> {
    return Effect.sync(() => {
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
    });
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
  const responseProducer = await Effect.runPromise(backend.createProducer<FlowResponse>({
    topic: topics.flowResponse,
  }));
  await Effect.runPromise(
    SynchronizedRef.update(service.state, (state) => ({
      ...state,
      responseProducer,
    })),
  );
};

describe("FlowManagerService operations", () => {
  it("dispatches all flow operations through the Match-backed handler", async () => {
    const configClient = new RecordingConfigClient(
      [
        {
          key: "custom",
          value: "{\"description\":\"Custom\",\"topics\":{\"input\":\"topic.in\"}}",
        },
      ],
      [
        {
          key: "flow-a",
          value: "{\"blueprint-name\":\"custom\",\"description\":\"Alpha\",\"parameters\":{\"limit\":3}}",
        },
      ],
    );
    const service = makeService();
    await seedConfigClient(service, configClient);

    await expect(Effect.runPromise(service.handleOperationEffect({operation: "list-blueprints"}))).resolves.toEqual({
      "blueprint-names": ["custom", "default"],
    });
    await expect(Effect.runPromise(service.handleOperationEffect({
      operation: "get-blueprint",
      "blueprint-name": "custom",
    }))).resolves.toMatchObject({
      "blueprint-definition": "{\"description\":\"Custom\",\"topics\":{\"input\":\"topic.in\"}}",
    });
    await expect(Effect.runPromise(service.handleOperationEffect({
      operation: "put-blueprint",
      "blueprint-name": "added",
      "blueprint-definition": {description: "Added", topics: {input: "topic.added"}},
    }))).resolves.toEqual({});
    await expect(Effect.runPromise(service.handleOperationEffect({
      operation: "delete-blueprint",
      "blueprint-name": "custom",
    }))).resolves.toEqual({});
    await expect(Effect.runPromise(service.handleOperationEffect({operation: "list-flows"}))).resolves.toEqual({
      "flow-ids": ["flow-a"],
    });
    await expect(Effect.runPromise(service.handleOperationEffect({
      operation: "get-flow",
      "flow-id": "flow-a",
    }))).resolves.toEqual({
      flow: "{\"blueprint-name\":\"custom\",\"description\":\"Alpha\",\"parameters\":{\"limit\":3}}",
    });
    await expect(Effect.runPromise(service.handleOperationEffect({
      operation: "start-flow",
      "flow-id": "flow-b",
      "blueprint-name": "custom",
    }))).resolves.toEqual({});
    await expect(Effect.runPromise(service.handleOperationEffect({
      operation: "stop-flow",
      "flow-id": "flow-a",
    }))).resolves.toEqual({});
    await expect(Effect.runPromise(service.handleOperationEffect({operation: "unknown-flow"}))).rejects.toMatchObject({
      _tag: "FlowManagerError",
      operation: "operation",
      message: "Unknown flow operation: unknown-flow",
    });

    expect(configClient.requests.some((request) =>
      request.operation === "put" && request.keys?.[0] === "flow-blueprint"
    )).toBe(true);
    expect(configClient.requests.some((request) =>
      request.operation === "delete" && request.keys?.[0] === "flow-blueprint"
    )).toBe(true);
  });

  it("uses tagged errors for invalid flow mutations", async () => {
    const service = makeService();

    const startError = await Effect.runPromise(service.handleStartFlowEffect({operation: "start-flow"}))
      .catch((caught: unknown) => caught);
    const stopError = await Effect.runPromise(service.handleStopFlowEffect({operation: "stop-flow"}))
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

    await Effect.runPromise(service.handleStartFlowEffect({
      operation: "start-flow",
      "flow-id": "flow-a",
      description: "alpha",
      parameters: {limit: 3},
    }));
    let state = await Effect.runPromise(SynchronizedRef.get(service.state));
    expect(Option.getOrUndefined(HashMap.get(state.flows, "flow-a"))).toMatchObject({
      id: "flow-a",
      blueprintName: "default",
      description: "alpha",
      parameters: {limit: 3},
      status: "running",
    });

    await Effect.runPromise(service.handleStopFlowEffect({
      operation: "stop-flow",
      "flow-id": "flow-a",
    }));
    state = await Effect.runPromise(SynchronizedRef.get(service.state));

    expect(HashMap.has(state.flows, "flow-a")).toBe(false);
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

    await Effect.runPromise(service.refreshBlueprintsFromConfigEffect);
    const state = await Effect.runPromise(SynchronizedRef.get(service.state));

    expect(Option.getOrUndefined(HashMap.get(state.blueprints, "custom"))).toMatchObject({
      description: "Custom",
      topics: {input: "topic.in"},
      extra: true,
    });
    expect(HashMap.has(state.blueprints, "broken")).toBe(false);
    expect(HashMap.has(state.blueprints, "default")).toBe(true);
  });

  it("serializes duplicate starts through the ref-backed map", async () => {
    const configClient = new RecordingConfigClient();
    const service = makeService();
    await seedConfigClient(service, configClient);

    const results = await Promise.allSettled([
      Effect.runPromise(service.handleStartFlowEffect({operation: "start-flow", "flow-id": "flow-a"})),
      Effect.runPromise(service.handleStartFlowEffect({operation: "start-flow", "flow-id": "flow-a"})),
    ]);
    const state = await Effect.runPromise(SynchronizedRef.get(service.state));

    expect(Option.getOrUndefined(HashMap.get(state.flows, "flow-a"))).toMatchObject({id: "flow-a"});
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
