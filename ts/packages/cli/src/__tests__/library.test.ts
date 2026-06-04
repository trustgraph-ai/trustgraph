import { describe, expect, it } from "vitest";
import { guessMimeType } from "../commands/library.js";

describe("library CLI helpers", () => {
  it("detects known MIME types through the Match-backed extension mapper", () => {
    expect(guessMimeType("paper.pdf")).toBe("application/pdf");
    expect(guessMimeType("notes.TXT")).toBe("text/plain");
    expect(guessMimeType("readme.md")).toBe("text/markdown");
    expect(guessMimeType("index.html")).toBe("text/html");
    expect(guessMimeType("partial.htm")).toBe("text/html");
    expect(guessMimeType("data.json")).toBe("application/json");
    expect(guessMimeType("table.csv")).toBe("text/csv");
    expect(guessMimeType("brief.docx")).toBe(
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    );
  });

  it("falls back for unknown or extensionless paths", () => {
    expect(guessMimeType("archive.bin")).toBe("application/octet-stream");
    expect(guessMimeType("README")).toBe("application/octet-stream");
  });
});
