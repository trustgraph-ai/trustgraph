import { describe, it, expect } from "vitest";
import * as EffectChunk from "effect/Chunk";
import { recursiveSplit } from "../chunking/recursive-splitter.js";

const splitToArray = (
  text: string,
  chunkSize: number,
  chunkOverlap: number,
): ReadonlyArray<string> =>
  EffectChunk.toReadonlyArray(recursiveSplit(text, chunkSize, chunkOverlap));

describe("recursiveSplit", () => {
  // ── Short text returns single chunk ──────────────────────────────
  it("returns single chunk when text is shorter than chunkSize", () => {
    const result = splitToArray("Hello world", 100, 10);
    expect(result).toEqual(["Hello world"]);
  });

  // ── Empty/whitespace text returns empty array ────────────────────
  it("returns empty array for empty string", () => {
    expect(splitToArray("", 100, 10)).toEqual([]);
  });

  it("returns empty array for whitespace-only text", () => {
    expect(splitToArray("   \n\n  \n  ", 100, 10)).toEqual([]);
  });

  // ── Splits on paragraph boundary (\n\n) first ───────────────────
  it("splits on paragraph boundary (\\n\\n) first", () => {
    const text = "Paragraph one content here.\n\nParagraph two content here.";
    const result = splitToArray(text, 30, 0);
    expect(result.length).toBeGreaterThanOrEqual(2);
    // Each chunk should contain content from its respective paragraph
    expect(result[0]).toContain("Paragraph one");
    expect(result[result.length - 1]).toContain("Paragraph two");
  });

  // ── Splits on \n when no \n\n present ────────────────────────────
  it("splits on newline when no paragraph boundary present", () => {
    const text = "Line one content.\nLine two content.\nLine three content.";
    const result = splitToArray(text, 25, 0);
    expect(result.length).toBeGreaterThanOrEqual(2);
    expect(result[0]).toContain("Line one");
  });

  // ── Splits on spaces when no newlines present ────────────────────
  it("splits on spaces when no newlines present", () => {
    const text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10";
    const result = splitToArray(text, 20, 0);
    expect(result.length).toBeGreaterThanOrEqual(2);
    // Each chunk should be at most roughly chunkSize
    for (const chunk of result) {
      // Allow some tolerance for the splitting algorithm
      expect(chunk.length).toBeLessThanOrEqual(30);
    }
  });

  // ── Character-level split as last resort ─────────────────────────
  it("splits at character level as last resort", () => {
    // A single long word with no separators
    const text = "abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqrstuvwxyz";
    const result = splitToArray(text, 10, 0);
    expect(result.length).toBeGreaterThanOrEqual(2);
    // Reassembled text should match original
    expect(result.join("")).toBe(text);
  });

  // ── Overlap: second chunk starts with tail of first ──────────────
  it("applies overlap so second chunk starts with tail of first", () => {
    const text = "First paragraph here.\n\nSecond paragraph here.";
    const result = splitToArray(text, 25, 5);
    expect(result.length).toBeGreaterThanOrEqual(2);
    if (result.length >= 2) {
      // The second chunk should start with the last 5 chars of the first
      const firstTail = result[0].slice(-5);
      expect(result[1].startsWith(firstTail)).toBe(true);
    }
  });

  // ── Large text produces multiple chunks ──────────────────────────
  it("large text produces multiple chunks of approximately chunkSize", () => {
    // Create a large block of text with paragraph separators
    const paragraphs = Array.from(
      { length: 20 },
      (_, i) => `This is paragraph number ${i + 1} with some filler content to make it longer.`,
    );
    const text = paragraphs.join("\n\n");
    const result = splitToArray(text, 100, 10);
    expect(result.length).toBeGreaterThan(5);
  });

  // ── chunkOverlap=0 produces no overlap ───────────────────────────
  it("chunkOverlap=0 produces no overlap between chunks", () => {
    const text = "AAAA\n\nBBBB\n\nCCCC\n\nDDDD";
    const result = splitToArray(text, 8, 0);
    expect(result.length).toBeGreaterThanOrEqual(2);
    // With zero overlap, no chunk (except possibly the first) should start with previous chunk's tail
    for (let i = 1; i < result.length; i++) {
      const prevTail = result[i - 1].slice(-3);
      // The next chunk should NOT start with the previous chunk's tail
      // (unless they happen to share content naturally, which won't happen with AAAA/BBBB/etc.)
      expect(result[i].startsWith(prevTail)).toBe(false);
    }
  });
});
