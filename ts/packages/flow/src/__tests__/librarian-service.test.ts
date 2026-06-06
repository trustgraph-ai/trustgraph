import {mkdtemp, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {Effect} from "effect";
import {describe, expect, it} from "vitest";
import {
  type BackendConsumer,
  type BackendProducer,
  type CreateConsumerOptions,
  type CreateProducerOptions,
  type DocumentMetadata,
  type Message,
  type PubSubBackend,
  type Triple,
} from "@trustgraph/base";
import {makeLibrarianService} from "../librarian/service.js";

class NoopPubSub implements PubSubBackend {
  createProducer<T>(_options: CreateProducerOptions<T>): Effect.Effect<BackendProducer<T>> {
    return Effect.succeed({
      send: () => Effect.void,
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
  s: {type: "IRI", iri: "https://example.test/doc"},
  p: {type: "IRI", iri: "https://example.test/title"},
  o: {type: "LITERAL", value: "Document"},
};

const sampleDocument: DocumentMetadata = {
  id: "doc-a",
  time: 1,
  kind: "text/plain",
  title: "Document A",
  comments: "",
  user: "alice",
  tags: [],
};

const makeService = (dataDir: string) =>
  makeLibrarianService({
    id: "librarian-test",
    manageProcessSignals: false,
    pubsub: new NoopPubSub(),
    dataDir,
  });

describe("LibrarianService schema-backed boundaries", () => {
  it("dispatches librarian operations through the Match-backed handler", async () => {
    const dir = await mkdtemp(join(tmpdir(), "trustgraph-librarian-service-"));
    const service = makeService(dir);

    try {
      await expect(Effect.runPromise(service.handleLibrarianOperation({
        operation: "list-documents",
        user: "alice",
      }))).resolves.toEqual({
        documents: [],
        "document-metadatas": [],
      });

      const upload = await Effect.runPromise(service.handleLibrarianOperation({
        operation: "begin-upload",
        documentMetadata: sampleDocument,
        "document-metadata": sampleDocument,
        "total-size": 12,
        "chunk-size": 4,
      }));
      await expect(Effect.runPromise(service.handleLibrarianOperation({
        operation: "get-upload-status",
        "upload-id": upload["upload-id"],
      }))).resolves.toMatchObject({
        "upload-id": upload["upload-id"],
        "upload-state": "in-progress",
        "missing-chunks": [0, 1, 2],
      });

      await expect(Effect.runPromise(service.handleLibrarianOperation({
        operation: "stream-document",
        "document-id": "doc-a",
      }))).rejects.toMatchObject({
        _tag: "LibrarianServiceError",
        operation: "stream-document",
        message: "stream-document must be handled as a streaming operation",
      });

      await expect(Effect.runPromise(service.handleLibrarianOperation(JSON.parse(`{"operation":"unknown-librarian"}`)))).rejects.toMatchObject({
        _tag: "LibrarianServiceError",
        operation: "operation",
        message: "Unknown librarian operation: unknown-librarian",
      });
    } finally {
      await rm(dir, {recursive: true, force: true});
    }
  });

  it("dispatches collection operations through the Match-backed handler", async () => {
    const dir = await mkdtemp(join(tmpdir(), "trustgraph-librarian-service-"));
    const service = makeService(dir);

    try {
      await expect(Effect.runPromise(service.handleCollectionOperation({
        operation: "update-collection",
        user: "alice",
        collection: "docs",
        name: "Docs",
        description: "Documentation",
        tags: ["reference"],
      }))).resolves.toEqual({
        collections: [{
          user: "alice",
          collection: "docs",
          name: "Docs",
          description: "Documentation",
          tags: ["reference"],
        }],
      });

      await expect(Effect.runPromise(service.handleCollectionOperation({
        operation: "list-collections",
        user: "alice",
      }))).resolves.toEqual({
        collections: [{
          user: "alice",
          collection: "docs",
          name: "Docs",
          description: "Documentation",
          tags: ["reference"],
        }],
      });

      await expect(Effect.runPromise(service.handleCollectionOperation({
        operation: "delete-collection",
        user: "alice",
        collection: "docs",
      }))).resolves.toEqual({});
      await expect(Effect.runPromise(service.handleCollectionOperation({
        operation: "list-collections",
        user: "alice",
      }))).resolves.toEqual({collections: []});

      await expect(Effect.runPromise(service.handleCollectionOperation(JSON.parse(`{"operation":"unknown-collection"}`)))).rejects.toMatchObject({
        _tag: "LibrarianServiceError",
        operation: "collection-operation",
        message: "Unknown collection operation: unknown-collection",
      });
    } finally {
      await rm(dir, {recursive: true, force: true});
    }
  });

  it("returns modeled upload fields without response assertions", async () => {
    const dir = await mkdtemp(join(tmpdir(), "trustgraph-librarian-service-"));
    const service = makeService(dir);

    const response = await Effect.runPromise(service.beginUpload({
      operation: "begin-upload",
      documentMetadata: sampleDocument,
      "document-metadata": sampleDocument,
      "total-size": 12,
      "chunk-size": 4,
    }));
    const uploadId = response["upload-id"];
    const status = await Effect.runPromise(service.getUploadStatus({
      operation: "get-upload-status",
      "upload-id": uploadId,
    }));
    await rm(dir, {recursive: true, force: true});

    expect(uploadId).toEqual(expect.any(String));
    expect(response).toMatchObject({
      "chunk-size": 4,
      "total-chunks": 3,
    });
    expect(status).toMatchObject({
      "upload-id": uploadId,
      "upload-state": "in-progress",
      "missing-chunks": [0, 1, 2],
    });
  });

  it("loads persisted state through concrete schemas", async () => {
    const dir = await mkdtemp(join(tmpdir(), "trustgraph-librarian-service-"));
    await Bun.write(
      join(dir, "librarian-state.json"),
      `{"documents":{"doc-a":{"id":"doc-a","time":1,"kind":"text/plain","title":"Document A","comments":"","user":"alice","tags":[]}},"processing":{},"collections":[{"user":"alice","collection":"default","name":"Default","description":"","tags":[]}]}`,
    );
    const service = makeService(dir);

    await Effect.runPromise(service.loadFromDisk);
    const documents = (await Effect.runPromise(service.listDocuments({operation: "list-documents", user: "alice"}))).documents;
    await rm(dir, {recursive: true, force: true});

    expect(documents).toEqual([{
      ...sampleDocument,
      documentType: "source",
      "document-type": "source",
    }]);
  });

  it("normalises document metadata through triple schema decoding", async () => {
    const dir = await mkdtemp(join(tmpdir(), "trustgraph-librarian-service-"));
    const service = makeService(dir);

    const valid = await Effect.runPromise(service.normaliseDocumentMetadata({
      ...sampleDocument,
      metadata: [sampleTriple],
    }));
    const invalid = await Effect.runPromise(service.normaliseDocumentMetadata({
      ...sampleDocument,
      id: "doc-b",
      metadata: [{not: "a triple"}],
    }));
    await rm(dir, {recursive: true, force: true});

    expect(valid.metadata).toEqual([sampleTriple]);
    expect(invalid.metadata).toBeUndefined();
  });
});
