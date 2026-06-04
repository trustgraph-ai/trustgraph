import { describe, expect, it } from "vitest";
import { makeStreamingReActParser } from "../agent/react/parser.js";

describe("StreamingReActParser", () => {
  it("routes split marker content through the Match-backed emitter", () => {
    const thought: string[] = [];
    const action: string[] = [];
    const actionInput: string[] = [];
    const finalAnswer: string[] = [];
    const parser = makeStreamingReActParser(
      (text) => thought.push(text),
      (text) => action.push(text),
      (text) => actionInput.push(text),
      (text) => finalAnswer.push(text),
    );

    parser.feed("Tho");
    expect(thought).toEqual([]);

    parser.feed("ught: plan\nAction: Search\nAction Input: {\"query\":\"alpha\"}\n");
    parser.feed("Final Answer: done");
    parser.flush();

    expect(thought).toEqual(["plan"]);
    expect(action).toEqual(["Search"]);
    expect(actionInput).toEqual(["{\"query\":\"alpha\"}"]);
    expect(finalAnswer).toEqual(["done"]);
  });

  it("treats pre-marker content as thought and routes continuations", () => {
    const events: Array<readonly [string, string]> = [];
    const parser = makeStreamingReActParser(
      (text) => events.push(["thought", text]),
      (text) => events.push(["action", text]),
      (text) => events.push(["action_input", text]),
      (text) => events.push(["final_answer", text]),
    );

    parser.feed("opening thought\n");
    parser.feed("continued thought\n");
    parser.feed("Action: Lookup\n");
    parser.feed("more lookup words\n");
    parser.feed("Action Input: first\n");
    parser.feed("second\n");
    parser.flush();

    expect(events).toEqual([
      ["thought", "opening thought"],
      ["thought", "continued thought"],
      ["action", "Lookup"],
      ["action", "more lookup words"],
      ["action_input", "first"],
      ["action_input", "second"],
    ]);
  });
});
