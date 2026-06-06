import { describe, expect, it } from "vitest";
import { guessMimeType } from "../commands/library.js";

describe("library CLI helpers", () => {
  it("keeps library load -t assigned to title while token remains long-only", () => {
    const result = Bun.spawnSync({
      cmd: ["bun", "src/index.ts", "library", "load", "--help"],
      cwd: new URL("../../", import.meta.url).pathname,
      stdout: "pipe",
      stderr: "pipe",
    });

    const stdout = result.stdout.toString();
    const stderr = result.stderr.toString();

    expect(result.exitCode).toBe(0);
    expect(stderr).toBe("");
    expect(stdout).toContain("--title");
    expect(stdout).toContain("-t");
    expect(stdout).toContain("--token");
    expect(stdout).not.toContain("-t, --token");
  });

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
