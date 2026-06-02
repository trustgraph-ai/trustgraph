import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
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
  async createProducer<T>(_options: CreateProducerOptions): Promise<BackendProducer<T>> {
    return {
      send: async () => undefined,
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

    const putError = await service.handlePut({ operation: "put" } as ConfigRequest)
      .catch((caught: unknown) => caught);
    const deleteError = await service.handleDelete({ operation: "delete" } as ConfigRequest)
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

    await service.handlePut({
      operation: "put",
      values: [
        { workspace: "alpha", type: "prompt", key: "system", value: "hello" },
      ],
    } as ConfigRequest);

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

    await service.loadFromDisk();
    const response = service.handleGet({
      operation: "get",
      keys: ["prompt", "system"],
    } as ConfigRequest);
    await rm(dir, { recursive: true, force: true });

    expect(response).toEqual({
      version: 7,
      values: {
        system: "legacy",
      },
    });
  });
});
