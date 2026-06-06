import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Effect, SynchronizedRef } from "effect";
import { describe, expect, it } from "vitest";
import { topics } from "@trustgraph/base";
import {
  ConfigServiceError,
  makeConfigService,
} from "../config/service.js";
import type {
  BackendConsumer,
  BackendProducer,
  ConfigRequest,
  CreateConsumerOptions,
  CreateProducerOptions,
  PubSubBackend,
} from "@trustgraph/base";

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

const makeService = (persistPath?: string) =>
  makeConfigService({
    id: "config-test",
    manageProcessSignals: false,
    pubsub: new NoopPubSub(),
    ...(persistPath === undefined ? {} : { persistPath }),
  });

describe("ConfigService operations", () => {
  it("uses tagged errors for invalid mutations", async () => {
    const service = makeService();
    const putRequest: ConfigRequest = { operation: "put" };
    const deleteRequest: ConfigRequest = { operation: "delete" };

    const putError = await Effect.runPromise(service.handlePutEffect(putRequest))
      .catch((caught: unknown) => caught);
    const deleteError = await Effect.runPromise(service.handleDeleteEffect(deleteRequest))
      .catch((caught: unknown) => caught);

    expect(putError).toBeInstanceOf(ConfigServiceError);
    expect(putError).toMatchObject({ _tag: "ConfigServiceError", operation: "put" });
    expect(deleteError).toBeInstanceOf(ConfigServiceError);
    expect(deleteError).toMatchObject({ _tag: "ConfigServiceError", operation: "delete" });
  });

  it("persists the workspace-aware config shape through Effect.tryPromise", async () => {
    const dir = await mkdtemp(join(tmpdir(), "trustgraph-config-service-"));
    const persistPath = join(dir, "config.json");
    const service = makeService(persistPath);
    const putRequest: ConfigRequest = {
      operation: "put",
      values: [
        { workspace: "alpha", type: "prompt", key: "system", value: "hello" },
      ],
    };

    await Effect.runPromise(service.handlePutEffect(putRequest));

    const persisted = await Bun.file(persistPath).json();
    await rm(dir, { recursive: true, force: true });

    expect(persisted).toEqual({
      version: 1,
      workspaces: {
        alpha: {
          prompt: {
            system: "hello",
          },
        },
      },
    });
  });

  it("loads the legacy persisted data shape without try/catch", async () => {
    const dir = await mkdtemp(join(tmpdir(), "trustgraph-config-service-"));
    const persistPath = join(dir, "config.json");
    await Bun.write(
      persistPath,
      `{"version":7,"data":{"prompt":{"system":"legacy"}}}`,
    );
    const service = makeService(persistPath);

    await Effect.runPromise(service.loadFromDiskEffect);
    const getRequest: ConfigRequest = {
      operation: "get",
      keys: ["prompt", "system"],
    };
    const response = service.handleGet(getRequest);
    await rm(dir, { recursive: true, force: true });

    expect(response).toEqual({
      version: 7,
      values: {
        system: "legacy",
      },
    });
  });

  it("serializes concurrent mutations through ref-backed state", async () => {
    const service = makeService();
    const requests: Array<ConfigRequest> = [
      { operation: "put", values: [{ type: "prompt", key: "a", value: "one" }] },
      { operation: "put", values: [{ type: "prompt", key: "b", value: "two" }] },
      { operation: "put", values: [{ workspace: "beta", type: "prompt", key: "c", value: "three" }] },
    ];

    await Effect.runPromise(Effect.all(requests.map((request) => service.handlePutEffect(request)), {
      concurrency: "unbounded",
      discard: true,
    }));

    expect(service.handleGet({ operation: "get", keys: ["prompt"] })).toEqual({
      version: 3,
      values: {
        a: "one",
        b: "two",
      },
    });
    expect(service.handleGetValuesAllWorkspaces({ operation: "getvalues-all-ws", keys: ["prompt"] }).values).toEqual([
      { workspace: "default", type: "prompt", key: "a", value: "one" },
      { workspace: "default", type: "prompt", key: "b", value: "two" },
      { workspace: "beta", type: "prompt", key: "c", value: "three" },
    ]);
  });

  it("dispatches all config operations through the Match-backed handler", async () => {
    const service = makeService();

    await expect(Effect.runPromise(service.handleOperationEffect({ operation: "put" }))).rejects.toMatchObject({
      _tag: "ConfigServiceError",
      operation: "put",
    });
    await expect(Effect.runPromise(service.handleOperationEffect({ operation: "delete" }))).rejects.toMatchObject({
      _tag: "ConfigServiceError",
      operation: "delete",
    });

    await expect(Effect.runPromise(service.handleOperationEffect({
      operation: "put",
      values: [{ type: "prompt", key: "system", value: "hello" }],
    }))).resolves.toEqual({ version: 1 });

    await expect(Effect.runPromise(service.handleOperationEffect({
      operation: "get",
      keys: ["prompt", "system"],
    }))).resolves.toEqual({
      version: 1,
      values: { system: "hello" },
    });
    await expect(Effect.runPromise(service.handleOperationEffect({ operation: "list" }))).resolves.toEqual({
      version: 1,
      directory: ["prompt"],
    });
    await expect(Effect.runPromise(service.handleOperationEffect({ operation: "config" }))).resolves.toEqual({
      version: 1,
      config: { prompt: { system: "hello" } },
    });
    await expect(Effect.runPromise(service.handleOperationEffect({
      operation: "getvalues",
      type: "prompt",
    }))).resolves.toEqual({
      version: 1,
      values: [{ type: "prompt", key: "system", value: "hello" }],
    });
    await expect(Effect.runPromise(service.handleOperationEffect({
      operation: "getvalues-all-ws",
      type: "prompt",
    }))).resolves.toEqual({
      version: 1,
      values: [{ workspace: "default", type: "prompt", key: "system", value: "hello" }],
    });
    await expect(Effect.runPromise(service.handleOperationEffect({
      operation: "delete",
      keys: ["prompt", "system"],
    }))).resolves.toEqual({ version: 2 });
  });

  it("pushes config from the stored producer handle", async () => {
    const backend = new NoopPubSub();
    const service = makeConfigService({
      id: "config-test",
      manageProcessSignals: false,
      pubsub: backend,
    });
    const pushProducer = await Effect.runPromise(backend.createProducer<{
      readonly version: number;
      readonly config: Record<string, unknown>;
    }>({ topic: topics.configPush }));

    await Effect.runPromise(
      SynchronizedRef.update(service.state, (state) => ({
        ...state,
        pushProducer,
      })),
    );
    await Effect.runPromise(service.pushConfigEffect);
    await Effect.runPromise(service.handlePutEffect({
      operation: "put",
      values: [{ type: "prompt", key: "system", value: "hello" }],
    }));

    expect(backend.sentByTopic.get(topics.configPush)).toEqual([
      { version: 0, config: {} },
      { version: 1, config: { prompt: { system: "hello" } } },
    ]);
  });
});
