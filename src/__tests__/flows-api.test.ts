import { describe, it, expect, vi, beforeEach } from "vitest";
import { FlowsApi } from "../socket/trustgraph-socket";
import { FlowResponse } from "../models/messages";

describe("FlowsApi", () => {
  let mockApi: {
    makeRequest: ReturnType<typeof vi.fn>;
  };
  let flowsApi: FlowsApi;

  beforeEach(() => {
    mockApi = {
      makeRequest: vi.fn(),
    };
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    flowsApi = new FlowsApi(mockApi as any);
  });

  describe("startFlow", () => {
    it("should call makeRequest with correct types and parameters", async () => {
      const mockResponse: FlowResponse = {
        flow: "started",
        description: "Flow started successfully",
      };
      mockApi.makeRequest.mockResolvedValue(mockResponse);

      const result = await flowsApi.startFlow(
        "test-flow-id",
        "test-class",
        "Test description",
      );

      expect(mockApi.makeRequest).toHaveBeenCalledWith(
        "flow",
        {
          operation: "start-flow",
          "flow-id": "test-flow-id",
          "blueprint-name": "test-class",
          description: "Test description",
        },
        30000,
      );
      expect(result).toEqual(mockResponse);
    });

    it("should use FlowRequest and FlowResponse types", async () => {
      const mockResponse: FlowResponse = {};
      mockApi.makeRequest.mockResolvedValue(mockResponse);

      await flowsApi.startFlow("id", "class", "desc");

      // Verify the call signature matches FlowRequest/FlowResponse types
      const callArgs = mockApi.makeRequest.mock.calls[0];
      const request = callArgs[1];

      // These properties should match FlowRequest interface
      expect(request).toHaveProperty("operation");
      expect(request).toHaveProperty("flow-id");
      expect(request).toHaveProperty("blueprint-name");
      expect(request).toHaveProperty("description");
    });
  });

  describe("stopFlow", () => {
    it("should call makeRequest with correct types and parameters", async () => {
      const mockResponse: FlowResponse = {
        flow: "stopped",
        description: "Flow stopped successfully",
      };
      mockApi.makeRequest.mockResolvedValue(mockResponse);

      const result = await flowsApi.stopFlow("test-flow-id");

      expect(mockApi.makeRequest).toHaveBeenCalledWith(
        "flow",
        {
          operation: "stop-flow",
          "flow-id": "test-flow-id",
        },
        30000,
      );
      expect(result).toEqual(mockResponse);
    });

    it("should use FlowRequest and FlowResponse types", async () => {
      const mockResponse: FlowResponse = {};
      mockApi.makeRequest.mockResolvedValue(mockResponse);

      await flowsApi.stopFlow("id");

      // Verify the call signature matches FlowRequest/FlowResponse types
      const callArgs = mockApi.makeRequest.mock.calls[0];
      const request = callArgs[1];

      // These properties should match FlowRequest interface
      expect(request).toHaveProperty("operation");
      expect(request).toHaveProperty("flow-id");
    });
  });

  describe("getFlows", () => {
    it("should return flow-ids array from response", async () => {
      const mockResponse: FlowResponse = {
        "flow-ids": ["flow1", "flow2", "flow3"],
      };
      mockApi.makeRequest.mockResolvedValue(mockResponse);

      const result = await flowsApi.getFlows();

      expect(mockApi.makeRequest).toHaveBeenCalledWith(
        "flow",
        {
          operation: "list-flows",
        },
        60000,
      );
      expect(result).toEqual(["flow1", "flow2", "flow3"]);
    });

    it("should return empty array when flow-ids is undefined", async () => {
      const mockResponse: FlowResponse = {};
      mockApi.makeRequest.mockResolvedValue(mockResponse);

      const result = await flowsApi.getFlows();

      expect(result).toEqual([]);
    });

    it("should handle response with flow-ids property correctly", async () => {
      // This test ensures we're accessing the hyphenated property name correctly
      const mockResponse = {
        "flow-ids": ["test-flow"],
        "other-property": "should-be-ignored",
      };
      mockApi.makeRequest.mockResolvedValue(mockResponse);

      const result = await flowsApi.getFlows();

      expect(result).toEqual(["test-flow"]);
    });
  });

  describe("getFlowBlueprints", () => {
    it("should return blueprint-names array from response", async () => {
      const mockResponse: FlowResponse = {
        "blueprint-names": ["class1", "class2"],
      };
      mockApi.makeRequest.mockResolvedValue(mockResponse);

      const result = await flowsApi.getFlowBlueprints();

      expect(mockApi.makeRequest).toHaveBeenCalledWith(
        "flow",
        {
          operation: "list-blueprints",
        },
        60000,
      );
      expect(result).toEqual(["class1", "class2"]);
    });

    it("should handle response with blueprint-names property correctly", async () => {
      // This test ensures we're accessing the hyphenated property name correctly
      const mockResponse = {
        "blueprint-names": ["test-class"],
        "other-property": "should-be-ignored",
      };
      mockApi.makeRequest.mockResolvedValue(mockResponse);

      const result = await flowsApi.getFlowBlueprints();

      expect(result).toEqual(["test-class"]);
    });
  });

  describe("getFlow", () => {
    it("should call makeRequest with correct parameters and parse JSON", async () => {
      const flowDefinition = { type: "flow", config: "test" };
      const mockResponse: FlowResponse = {
        flow: JSON.stringify(flowDefinition), // Must be valid JSON string
        description: "Test flow",
      };
      mockApi.makeRequest.mockResolvedValue(mockResponse);

      const result = await flowsApi.getFlow("test-flow-id");

      expect(mockApi.makeRequest).toHaveBeenCalledWith(
        "flow",
        {
          operation: "get-flow",
          "flow-id": "test-flow-id",
        },
        60000,
      );
      expect(result).toEqual(flowDefinition); // Result should be parsed JSON
    });
  });

  describe("getFlowBlueprint", () => {
    it("should call makeRequest with correct parameters and parse JSON", async () => {
      const blueprintDefinition = { type: "blueprint", name: "test-blueprint" };
      const mockResponse: FlowResponse = {
        "blueprint-definition": JSON.stringify(blueprintDefinition), // Must be valid JSON string
        description: "Test blueprint",
      };
      mockApi.makeRequest.mockResolvedValue(mockResponse);

      const result = await flowsApi.getFlowBlueprint("test-class");

      expect(mockApi.makeRequest).toHaveBeenCalledWith(
        "flow",
        {
          operation: "get-blueprint",
          "blueprint-name": "test-class",
        },
        60000,
      );
      expect(result).toEqual(blueprintDefinition); // Result should be parsed JSON
    });
  });
});
