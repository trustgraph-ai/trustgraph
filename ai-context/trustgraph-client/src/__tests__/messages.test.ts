import { describe, it, expect } from "vitest";
import type {
  RequestMessage,
  ApiResponse,
  TextCompletionRequest,
  TextCompletionResponse,
  GraphRagRequest,
  GraphRagResponse,
  AgentRequest,
  AgentResponse,
  EmbeddingsRequest,
  EmbeddingsResponse,
  GraphEmbeddingsQueryRequest,
  GraphEmbeddingsQueryResponse,
  TriplesQueryRequest,
  LoadDocumentRequest,
  LoadTextRequest,
  LibraryRequest,
  LibraryResponse,
  FlowRequest,
  FlowResponse,
  DocumentMetadata,
  ProcessingMetadata,
} from "../models/messages";

describe("Message Types", () => {
  describe("RequestMessage", () => {
    it("should have correct structure", () => {
      const message: RequestMessage = {
        id: "test-id",
        service: "test-service",
        request: { test: "data" },
      };

      expect(message.id).toBe("test-id");
      expect(message.service).toBe("test-service");
      expect(message.request).toEqual({ test: "data" });
    });
  });

  describe("ApiResponse", () => {
    it("should have correct structure", () => {
      const response: ApiResponse = {
        id: "test-id",
        response: { result: "success" },
      };

      expect(response.id).toBe("test-id");
      expect(response.response).toEqual({ result: "success" });
    });
  });

  describe("TextCompletionRequest", () => {
    it("should have correct structure", () => {
      const request: TextCompletionRequest = {
        system: "You are a helpful assistant",
        prompt: "Hello, world!",
      };

      expect(request.system).toBe("You are a helpful assistant");
      expect(request.prompt).toBe("Hello, world!");
    });
  });

  describe("TextCompletionResponse", () => {
    it("should have correct structure", () => {
      const response: TextCompletionResponse = {
        response: "Hello! How can I help you today?",
      };

      expect(response.response).toBe("Hello! How can I help you today?");
    });
  });

  describe("GraphRagRequest", () => {
    it("should have correct structure with required query", () => {
      const request: GraphRagRequest = {
        query: "What is the capital of France?",
      };

      expect(request.query).toBe("What is the capital of France?");
    });

    it("should have correct structure with optional parameters", () => {
      const request: GraphRagRequest = {
        query: "What is the capital of France?",
        "entity-limit": 100,
        "triple-limit": 50,
        "max-subgraph-size": 2000,
        "max-path-length": 3,
      };

      expect(request.query).toBe("What is the capital of France?");
      expect(request["entity-limit"]).toBe(100);
      expect(request["triple-limit"]).toBe(50);
      expect(request["max-subgraph-size"]).toBe(2000);
      expect(request["max-path-length"]).toBe(3);
    });
  });

  describe("GraphRagResponse", () => {
    it("should have correct structure", () => {
      const response: GraphRagResponse = {
        response: "The capital of France is Paris.",
      };

      expect(response.response).toBe("The capital of France is Paris.");
    });
  });

  describe("AgentRequest", () => {
    it("should have correct structure", () => {
      const request: AgentRequest = {
        question: "What is the weather like today?",
      };

      expect(request.question).toBe("What is the weather like today?");
    });
  });

  describe("AgentResponse", () => {
    it("should have correct structure with all fields", () => {
      const response: AgentResponse = {
        thought: "I need to check the weather",
        observation: "Weather API shows sunny conditions",
        answer: "It is sunny today",
        error: undefined,
      };

      expect(response.thought).toBe("I need to check the weather");
      expect(response.observation).toBe("Weather API shows sunny conditions");
      expect(response.answer).toBe("It is sunny today");
      expect(response.error).toBeUndefined();
    });

    it("should handle error response", () => {
      const response: AgentResponse = {
        error: { type: "agent-error", message: "Weather service unavailable" },
      };

      expect(response.error?.message).toBe("Weather service unavailable");
      expect(response.error?.type).toBe("agent-error");
    });
  });

  describe("EmbeddingsRequest", () => {
    it("should have correct structure", () => {
      const request: EmbeddingsRequest = {
        texts: ["This is a test sentence for embedding", "Another text"],
      };

      expect(request.texts).toEqual(["This is a test sentence for embedding", "Another text"]);
    });
  });

  describe("EmbeddingsResponse", () => {
    it("should have correct structure", () => {
      // vectors[text_index][dimension_index] - one vector per input text
      const response: EmbeddingsResponse = {
        vectors: [
          [0.1, 0.2, 0.3],  // First text's vector
          [0.4, 0.5, 0.6],  // Second text's vector
        ],
      };

      expect(response.vectors).toEqual([
        [0.1, 0.2, 0.3],
        [0.4, 0.5, 0.6],
      ]);
    });
  });

  describe("GraphEmbeddingsQueryRequest", () => {
    it("should have correct structure", () => {
      const request: GraphEmbeddingsQueryRequest = {
        vector: [0.1, 0.2, 0.3],
        limit: 10,
      };

      expect(request.vector).toEqual([0.1, 0.2, 0.3]);
      expect(request.limit).toBe(10);
    });
  });

  describe("GraphEmbeddingsQueryResponse", () => {
    it("should have correct structure", () => {
      const response: GraphEmbeddingsQueryResponse = {
        entities: [
          { entity: { t: "i", i: "http://example.org/entity1" }, score: 0.95 },
          { entity: { t: "i", i: "http://example.org/entity2" }, score: 0.87 },
        ],
      };

      expect(response.entities).toHaveLength(2);
      expect(response.entities[0].score).toBe(0.95);
      expect(response.entities[0].entity?.t).toBe("i");
      expect((response.entities[0].entity as { t: "i"; i: string }).i).toBe("http://example.org/entity1");
      expect(response.entities[1].score).toBe(0.87);
    });
  });

  describe("TriplesQueryRequest", () => {
    it("should have correct structure with all fields", () => {
      const request: TriplesQueryRequest = {
        s: { t: "i", i: "http://example.org/subject" },
        p: { t: "i", i: "http://example.org/predicate" },
        o: { t: "l", v: "object value" },
        limit: 100,
      };

      expect((request.s as { t: "i"; i: string }).i).toBe("http://example.org/subject");
      expect((request.p as { t: "i"; i: string }).i).toBe("http://example.org/predicate");
      expect((request.o as { t: "l"; v: string }).v).toBe("object value");
      expect(request.limit).toBe(100);
    });

    it("should handle optional fields", () => {
      const request: TriplesQueryRequest = {
        limit: 50,
      };

      expect(request.s).toBeUndefined();
      expect(request.p).toBeUndefined();
      expect(request.o).toBeUndefined();
      expect(request.limit).toBe(50);
    });
  });

  describe("LoadDocumentRequest", () => {
    it("should have correct structure", () => {
      const request: LoadDocumentRequest = {
        id: "doc-123",
        data: "base64-encoded-document-data",
        metadata: [
          {
            s: { t: "i", i: "http://example.org/doc-123" },
            p: { t: "i", i: "http://example.org/title" },
            o: { t: "l", v: "Test Document" },
          },
        ],
      };

      expect(request.id).toBe("doc-123");
      expect(request.data).toBe("base64-encoded-document-data");
      expect(request.metadata).toHaveLength(1);
    });
  });

  describe("LoadTextRequest", () => {
    it("should have correct structure", () => {
      const request: LoadTextRequest = {
        id: "text-123",
        text: "This is some text to load",
        charset: "utf-8",
        metadata: [],
      };

      expect(request.id).toBe("text-123");
      expect(request.text).toBe("This is some text to load");
      expect(request.charset).toBe("utf-8");
      expect(request.metadata).toEqual([]);
    });
  });

  describe("DocumentMetadata", () => {
    it("should have correct structure", () => {
      const metadata: DocumentMetadata = {
        id: "doc-123",
        time: 1640995200000,
        kind: "pdf",
        title: "Test Document",
        comments: "A test document",
        metadata: [],
        user: "test-user",
        tags: ["test", "document"],
      };

      expect(metadata.id).toBe("doc-123");
      expect(metadata.time).toBe(1640995200000);
      expect(metadata.kind).toBe("pdf");
      expect(metadata.title).toBe("Test Document");
      expect(metadata.comments).toBe("A test document");
      expect(metadata.user).toBe("test-user");
      expect(metadata.tags).toEqual(["test", "document"]);
    });
  });

  describe("ProcessingMetadata", () => {
    it("should have correct structure", () => {
      const metadata: ProcessingMetadata = {
        id: "proc-123",
        "document-id": "doc-123",
        time: 1640995200000,
        flow: "default-flow",
        user: "test-user",
        collection: "test-collection",
        tags: ["processing", "test"],
      };

      expect(metadata.id).toBe("proc-123");
      expect(metadata["document-id"]).toBe("doc-123");
      expect(metadata.time).toBe(1640995200000);
      expect(metadata.flow).toBe("default-flow");
      expect(metadata.user).toBe("test-user");
      expect(metadata.collection).toBe("test-collection");
      expect(metadata.tags).toEqual(["processing", "test"]);
    });
  });

  describe("LibraryRequest", () => {
    it("should have correct structure", () => {
      const request: LibraryRequest = {
        operation: "list_documents",
        user: "test-user",
        collection: "test-collection",
      };

      expect(request.operation).toBe("list_documents");
      expect(request.user).toBe("test-user");
      expect(request.collection).toBe("test-collection");
    });
  });

  describe("LibraryResponse", () => {
    it("should have correct structure", () => {
      const response: LibraryResponse = {
        error: new Error(),
        "document-metadatas": [
          {
            id: "doc-1",
            title: "Document 1",
            time: 1640995200000,
          },
        ],
      };

      expect(response.error).toBeInstanceOf(Error);
      expect(response["document-metadatas"]).toHaveLength(1);
      expect(response["document-metadatas"]![0].id).toBe("doc-1");
    });
  });

  describe("FlowRequest", () => {
    it("should have correct structure", () => {
      const request: FlowRequest = {
        operation: "get_flow",
        "flow-id": "default-flow",
      };

      expect(request.operation).toBe("get_flow");
      expect(request["flow-id"]).toBe("default-flow");
    });
  });

  describe("FlowResponse", () => {
    it("should have correct structure", () => {
      const response: FlowResponse = {
        "flow-ids": ["flow-1", "flow-2"],
        flow: "flow-definition",
        description: "A test flow",
        error: undefined,
      };

      expect(response["flow-ids"]).toEqual(["flow-1", "flow-2"]);
      expect(response.flow).toBe("flow-definition");
      expect(response.description).toBe("A test flow");
      expect(response.error).toBeUndefined();
    });
  });
});
