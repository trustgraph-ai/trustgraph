import { describe, expect, it, vi } from "vitest";
import type {
  BaseApi,
} from "../socket/trustgraph-socket";
import {
  ConfigApi,
  KnowledgeApi,
  LibrarianApi,
} from "../socket/trustgraph-socket";

function makeApi() {
  const makeRequest = vi.fn();
  const base = {
    user: "alice",
    makeRequest,
  } as unknown as BaseApi;
  return { base, makeRequest };
}

describe("workbench API contracts", () => {
  describe("ConfigApi", () => {
    it("returns Python-style getvalues entries", async () => {
      const { base, makeRequest } = makeApi();
      makeRequest.mockResolvedValue({
        values: [{ type: "prompt", key: "welcome", value: "hello" }],
      });

      const result = await ConfigApi(base).getValues("prompt");

      expect(makeRequest).toHaveBeenCalledWith(
        "config",
        { operation: "getvalues", type: "prompt" },
        60000,
      );
      expect(result).toEqual([{ type: "prompt", key: "welcome", value: "hello" }]);
    });

    it("parses token-cost values stored as config JSON strings", async () => {
      const { base, makeRequest } = makeApi();
      makeRequest.mockResolvedValue({
        values: [
          {
            type: "token-cost",
            key: "gpt-test",
            value: JSON.stringify({ input_price: 0.1, output_price: 0.2 }),
          },
        ],
      });

      const result = await ConfigApi(base).getTokenCosts();

      expect(result).toEqual([
        { model: "gpt-test", input_price: 0.1, output_price: 0.2 },
      ]);
    });

    it("writes and deletes config using Python-style key/value arrays", async () => {
      const { base, makeRequest } = makeApi();
      makeRequest.mockResolvedValue({});
      const config = ConfigApi(base);

      await config.putConfig([{ type: "tool", key: "search", value: "{}" }]);
      await config.deleteConfig({ type: "tool", key: "search" });

      expect(makeRequest).toHaveBeenNthCalledWith(
        1,
        "config",
        {
          operation: "put",
          values: [{ type: "tool", key: "search", value: "{}" }],
        },
        60000,
      );
      expect(makeRequest).toHaveBeenNthCalledWith(
        2,
        "config",
        {
          operation: "delete",
          keys: [{ type: "tool", key: "search" }],
        },
        30000,
      );
    });
  });

  describe("LibrarianApi", () => {
    it("reads Python-style document and processing list responses", async () => {
      const { base, makeRequest } = makeApi();
      const document = { id: "doc-1", title: "Document" };
      const processing = { id: "proc-1", "document-id": "doc-1" };
      const librarian = LibrarianApi(base);

      makeRequest
        .mockResolvedValueOnce({ "document-metadatas": [document] })
        .mockResolvedValueOnce({ "processing-metadatas": [processing] });

      await expect(librarian.getDocuments()).resolves.toEqual([document]);
      await expect(librarian.getProcessing()).resolves.toEqual([processing]);
    });

    it("sends both kebab-case and camel-case document identifiers", async () => {
      const { base, makeRequest } = makeApi();
      const document = { id: "doc-1", title: "Document" };
      makeRequest.mockResolvedValue({ "document-metadata": document });

      const result = await LibrarianApi(base).getDocumentMetadata("doc-1");

      expect(makeRequest).toHaveBeenCalledWith(
        "librarian",
        {
          operation: "get-document-metadata",
          "document-id": "doc-1",
          documentId: "doc-1",
          user: "alice",
        },
        30000,
      );
      expect(result).toEqual(document);
    });

    it("uploads documents with Python and TypeScript metadata aliases", async () => {
      const { base, makeRequest } = makeApi();
      makeRequest.mockResolvedValue({});

      await LibrarianApi(base).loadDocument(
        "SGVsbG8=",
        "text/plain",
        "Hello",
        "comment",
        ["tag"],
        "doc-1",
      );

      const request = makeRequest.mock.calls[0]?.[1] as Record<string, unknown>;
      expect(request["document-metadata"]).toMatchObject({
        id: "doc-1",
        kind: "text/plain",
        title: "Hello",
        user: "alice",
        "document-type": "source",
        documentType: "source",
      });
      expect(request.documentMetadata).toEqual(request["document-metadata"]);
    });
  });

  describe("KnowledgeApi", () => {
    it("lists and loads document embedding cores", async () => {
      const { base, makeRequest } = makeApi();
      const knowledge = KnowledgeApi(base);

      makeRequest
        .mockResolvedValueOnce({ ids: ["de-core"] })
        .mockResolvedValueOnce({});

      await expect(knowledge.getDocumentEmbeddingCores()).resolves.toEqual(["de-core"]);
      await knowledge.loadDeCore("de-core", "default", "library");

      expect(makeRequest).toHaveBeenNthCalledWith(
        1,
        "knowledge",
        { operation: "list-de-cores", user: "alice" },
        60000,
      );
      expect(makeRequest).toHaveBeenNthCalledWith(
        2,
        "knowledge",
        {
          operation: "load-de-core",
          id: "de-core",
          flow: "default",
          user: "alice",
          collection: "library",
        },
        30000,
      );
    });

    it("unloads knowledge graph cores from a flow", async () => {
      const { base, makeRequest } = makeApi();
      makeRequest.mockResolvedValue({});

      await KnowledgeApi(base).unloadKgCore("kg-core", "default");

      expect(makeRequest).toHaveBeenCalledWith(
        "knowledge",
        {
          operation: "unload-kg-core",
          id: "kg-core",
          flow: "default",
          user: "alice",
        },
        30000,
      );
    });
  });
});
