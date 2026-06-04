import { describe, expect, it } from "@effect/vitest";
import { Effect } from "effect";
import { makeAgentRuntime, parseReActResponse } from "../agent/react/service.js";

const toolEntry = (entry: Record<string, unknown>): string =>
  JSON.stringify(entry);

describe("AgentService helpers", () => {
  it.effect(
    "loads configured tools through the Match-backed builder",
    Effect.fnUntraced(function* () {
      const runtime = yield* makeAgentRuntime;

      yield* runtime.configureTools({
        tool: {
          knowledge: toolEntry({
            type: "knowledge-query",
            name: "Knowledge",
          }),
          document: toolEntry({
            type: "document-query",
            name: "Document",
            description: "Find document context.",
          }),
          triples: toolEntry({
            type: "triples-query",
            name: "Triples",
          }),
          mcp: toolEntry({
            type: "mcp-tool",
            name: "Lookup",
            description: "Call an external lookup tool.",
            arguments: [
              {
                name: "query",
                type: "string",
                description: "Lookup query.",
              },
            ],
          }),
          unknown: toolEntry({
            type: "unknown-tool",
            name: "Ignored",
          }),
        },
      }, 1);

      const tools = yield* runtime.getConfiguredTools;

      expect(tools?.map((tool) => tool.name)).toEqual([
        "Knowledge",
        "Document",
        "Triples",
        "Lookup",
      ]);
      expect(tools?.map((tool) => tool.config?.type)).toEqual([
        "knowledge-query",
        "document-query",
        "triples-query",
        "mcp-tool",
      ]);
      expect(tools?.[0]?.description).toBe(
        "Query the knowledge graph for information about entities and their relationships.",
      );
      expect(tools?.[1]?.description).toBe("Find document context.");
      expect(tools?.[3]?.args).toEqual([
        {
          name: "query",
          type: "string",
          description: "Lookup query.",
        },
      ]);
    }),
  );

  it("parses ReAct continuation sections through the Match-backed parser", () => {
    const parsed = parseReActResponse([
      "Thought: first idea",
      "continued idea",
      "Action: Search",
      "extra action words",
      "Action Input: {\"question\":\"hello\"}",
      "continued input",
    ].join("\n"));

    expect(parsed).toEqual({
      thought: "first idea\ncontinued idea",
      action: "Search extra action words",
      actionInput: "{\"question\":\"hello\"}\ncontinued input",
      finalAnswer: "",
    });
  });

  it("parses final answers and ignores later text", () => {
    const parsed = parseReActResponse([
      "Thought: done",
      "Final Answer: answer one",
      "answer two",
      "Action: ignored",
    ].join("\n"));

    expect(parsed).toEqual({
      thought: "done",
      action: "",
      actionInput: "",
      finalAnswer: "answer one\nanswer two\nAction: ignored",
    });
  });
});
