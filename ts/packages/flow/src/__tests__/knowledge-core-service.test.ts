import {mkdtemp, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {Effect, HashMap, Option, SynchronizedRef} from "effect";
import {describe, expect, it} from "vitest";
import {
  topics,
  type BackendConsumer,
  type BackendProducer,
  type CreateConsumerOptions,
  type CreateProducerOptions,
  type KnowledgeRequest,
  type KnowledgeResponse,
  type Message,
  type PubSubBackend,
  type Triple,
} from "@trustgraph/base";
import {makeKnowledgeCoreService} from "../cores/service.js";

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
      acknowledge: (_message: Message<T>) => Effect.void,
      negativeAcknowledge: (_message: Message<T>) => Effect.void,
      unsubscribe: Effect.void,
      close: Effect.void,
    });
  }

  readonly close: Effect.Effect<void> = Effect.void;
}

const sampleTriple: Triple = {
  s: {type: "IRI", iri: "https://example.test/a"},
  p: {type: "IRI", iri: "https://example.test/related"},
  o: {type: "LITERAL", value: "alpha"},
};

const makeService = (dataDir: string, backend: PubSubBackend = new NoopPubSub()) =>
  makeKnowledgeCoreService({
    id: "knowledge-test",
    manageProcessSignals: false,
    pubsub: backend,
    dataDir,
  });

const seedResponseProducer = async (
  backend: NoopPubSub,
  service: ReturnType<typeof makeKnowledgeCoreService>,
) => {
  const responseProducer = await Effect.runPromise(backend.createProducer<KnowledgeResponse>({
    topic: topics.knowledgeResponse,
  }));
  await Effect.runPromise(
    SynchronizedRef.update(service.state, (state) => ({
      ...state,
      responseProducer,
    })),
  );
};

describe("KnowledgeCoreService operations", () => {
  it("stores knowledge cores through ref-backed state and preserves graph embedding aliases", async () => {
    const dir = await mkdtemp(join(tmpdir(), "trustgraph-knowledge-service-"));
    const backend = new NoopPubSub();
    const service = makeService(dir, backend);
    await seedResponseProducer(backend, service);

    const request: KnowledgeRequest = {
      operation: "put-kg-core",
      user: "alice",
      id: "core-a",
      triples: [sampleTriple],
      "graph-embeddings": [
        {
          entity: {type: "IRI", iri: "https://example.test/a"},
          vectors: [[1, 2, 3]],
        },
      ],
    };

    await Effect.runPromise(service.putKgCoreEffect(request, "put-1"));
    const state = await Effect.runPromise(SynchronizedRef.get(service.state));
    const core = Option.getOrUndefined(HashMap.get(state.kgCores, "alice:core-a"));

    await Effect.runPromise(service.getKgCoreEffect({
      operation: "get-kg-core",
      user: "alice",
      id: "core-a",
    }, "get-1"));
    await rm(dir, {recursive: true, force: true});

    expect(core?.triples).toEqual([sampleTriple]);
    expect(core?.graphEmbeddings).toEqual([
      {
        entity: {type: "IRI", iri: "https://example.test/a"},
        vectors: [[1, 2, 3]],
      },
    ]);
    expect(backend.sentByTopic.get(topics.knowledgeResponse)).toEqual([
      {},
      {
        triples: [sampleTriple],
        eos: false,
      },
      {
        graphEmbeddings: [
          {
            entity: {type: "IRI", iri: "https://example.test/a"},
            vectors: [[1, 2, 3]],
          },
        ],
        "graph-embeddings": [
          {
            entity: {type: "IRI", iri: "https://example.test/a"},
            vectors: [[1, 2, 3]],
          },
        ],
        eos: true,
      },
    ]);
  });

  it("serializes concurrent mutations through ref-backed maps", async () => {
    const dir = await mkdtemp(join(tmpdir(), "trustgraph-knowledge-service-"));
    const backend = new NoopPubSub();
    const service = makeService(dir, backend);
    await seedResponseProducer(backend, service);

    await Effect.runPromise(Effect.all([
      service.putKgCoreEffect({
        operation: "put-kg-core",
        user: "alice",
        id: "core-b",
        triples: [sampleTriple],
      }, "put-a"),
      service.putKgCoreEffect({
        operation: "put-kg-core",
        user: "alice",
        id: "core-b",
        triples: [
          {
            s: {type: "IRI", iri: "https://example.test/b"},
            p: {type: "IRI", iri: "https://example.test/related"},
            o: {type: "LITERAL", value: "beta"},
          },
        ],
      }, "put-b"),
    ], {
      concurrency: "unbounded",
      discard: true,
    }));

    const state = await Effect.runPromise(SynchronizedRef.get(service.state));
    await rm(dir, {recursive: true, force: true});

    expect(Option.getOrUndefined(HashMap.get(state.kgCores, "alice:core-b"))?.triples).toHaveLength(2);
  });

  it("loads the legacy persisted knowledge shape with schema decoding", async () => {
    const dir = await mkdtemp(join(tmpdir(), "trustgraph-knowledge-service-"));
    const persistPath = join(dir, "knowledge-state.json");
    await Bun.write(
      persistPath,
      JSON.stringify({
        "alice:legacy": {
          triples: [sampleTriple],
          graphEmbeddings: [],
        },
      }),
    );
    const service = makeService(dir);

    await Effect.runPromise(service.loadFromDiskEffect);
    const state = await Effect.runPromise(SynchronizedRef.get(service.state));
    await rm(dir, {recursive: true, force: true});

    expect(Option.getOrUndefined(HashMap.get(state.kgCores, "alice:legacy"))?.triples).toEqual([sampleTriple]);
  });
});
