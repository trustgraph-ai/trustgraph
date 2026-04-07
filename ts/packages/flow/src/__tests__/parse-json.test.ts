import { describe, it, expect, vi } from "vitest";
import { parseJsonResponse } from "../extract/knowledge-extract.js";

describe("parseJsonResponse", () => {
  // Suppress console.warn from the function under test
  beforeEach(() => {
    vi.spyOn(console, "warn").mockImplementation(() => {});
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ── Valid JSON array ────────────────────────────────────────────
  it("parses a valid JSON array", () => {
    const result = parseJsonResponse<{ a: number }[]>('[{"a":1}]');
    expect(result).toEqual([{ a: 1 }]);
  });

  // ── JSON with markdown fences ──────────────────────────────────
  it("strips markdown fences and parses JSON", () => {
    const input = '```json\n[{"a":1}]\n```';
    const result = parseJsonResponse<{ a: number }[]>(input);
    expect(result).toEqual([{ a: 1 }]);
  });

  // ── JSON embedded in surrounding text ──────────────────────────
  it("extracts JSON array embedded in surrounding text", () => {
    const input = 'Here is the result: [{"a":1}] hope that helps';
    const result = parseJsonResponse<{ a: number }[]>(input);
    expect(result).toEqual([{ a: 1 }]);
  });

  // ── Truncated array ────────────────────────────────────────────
  it("repairs truncated array by closing at last complete object", () => {
    const input = '[{"a":1},{"b":2';
    const result = parseJsonResponse<Record<string, number>[]>(input);
    expect(result).toEqual([{ a: 1 }]);
  });

  // ── Single object (not array) ──────────────────────────────────
  it("parses a single object directly (valid JSON passes Attempt 1)", () => {
    const input = '{"a":1}';
    const result = parseJsonResponse<{ a: number }>(input);
    // A bare object is valid JSON, so Attempt 1 (JSON.parse) succeeds directly
    expect(result).toEqual({ a: 1 });
  });

  it("wraps a single object in an array when embedded in non-JSON text", () => {
    // When the object is surrounded by garbage, Attempt 1 and 2 fail,
    // so Attempt 4 extracts the object and wraps it in an array
    const input = 'some text {"a":1} more text';
    const result = parseJsonResponse<{ a: number }[]>(input);
    expect(result).toEqual([{ a: 1 }]);
  });

  // ── Complete garbage ───────────────────────────────────────────
  it("returns null for complete garbage", () => {
    const result = parseJsonResponse("not json at all");
    expect(result).toBeNull();
  });

  // ── Empty string ───────────────────────────────────────────────
  it("returns null for empty string", () => {
    const result = parseJsonResponse("");
    expect(result).toBeNull();
  });

  // ── Nested fences with language tag ────────────────────────────
  it("parses JSON inside fences with language tag (single object)", () => {
    const input = '```json\n{"key":"value"}\n```';
    const result = parseJsonResponse<{ key: string }[]>(input);
    // The function first strips fences, then tries JSON.parse which yields an object,
    // then if that fails as array extraction, falls back to wrapping in array
    // Actually: JSON.parse of '{"key":"value"}' succeeds directly, returning the object
    expect(result).toEqual({ key: "value" });
  });

  // ── Multiple objects in valid array ────────────────────────────
  it("parses a multi-element array correctly", () => {
    const input = '[{"name":"Alice"},{"name":"Bob"},{"name":"Carol"}]';
    const result = parseJsonResponse<{ name: string }[]>(input);
    expect(result).toEqual([
      { name: "Alice" },
      { name: "Bob" },
      { name: "Carol" },
    ]);
  });

  // ── Fences without language tag ────────────────────────────────
  it("strips fences without a language tag", () => {
    const input = '```\n[{"x":42}]\n```';
    const result = parseJsonResponse<{ x: number }[]>(input);
    expect(result).toEqual([{ x: 42 }]);
  });
});
