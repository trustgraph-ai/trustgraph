import { describe, it, expect, vi } from "vitest";
import { textToBase64, fileToBase64 } from "../document-encoding";

describe("textToBase64", () => {
  it("should encode simple ASCII text to Base64", () => {
    const input = "Hello World";
    const result = textToBase64(input);
    expect(result).toBe("SGVsbG8gV29ybGQ=");
  });

  it("should encode UTF-8 text to Base64", () => {
    const input = "Hello 世界";
    const result = textToBase64(input);
    expect(result).toBe("SGVsbG8g5LiW55WM");
  });

  it("should encode empty string", () => {
    const result = textToBase64("");
    expect(result).toBe("");
  });

  it("should encode special characters", () => {
    const input = "!@#$%^&*()";
    const result = textToBase64(input);
    expect(result).toBe("IUAjJCVeJiooKQ==");
  });

  it("should handle newlines and tabs", () => {
    const input = "Line 1\nLine 2\tTabbed";
    const result = textToBase64(input);
    expect(result).toBe("TGluZSAxCkxpbmUgMglUYWJiZWQ=");
  });
});

describe("fileToBase64", () => {
  it("should convert file to Base64 string", async () => {
    const mockFile = new File(["Hello World"], "test.txt", {
      type: "text/plain",
    });

    // Mock FileReader
    const mockReader = {
      result: "data:text/plain;base64,SGVsbG8gV29ybGQ=",
      onloadend: null as (() => void) | null,
      readAsDataURL: vi.fn(),
    };

    vi.spyOn(window, "FileReader").mockImplementation(
      () => mockReader as Partial<FileReader>,
    );

    const promise = fileToBase64(mockFile);

    // Simulate file read completion
    mockReader.onloadend();

    const result = await promise;
    expect(result).toBe("SGVsbG8gV29ybGQ=");
    expect(mockReader.readAsDataURL).toHaveBeenCalledWith(mockFile);
  });

  it("should handle different MIME types", async () => {
    const mockFile = new File(["binary data"], "test.png", {
      type: "image/png",
    });

    const mockReader = {
      result:
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
      onloadend: null as (() => void) | null,
      readAsDataURL: vi.fn(),
    };

    vi.spyOn(window, "FileReader").mockImplementation(
      () => mockReader as Partial<FileReader>,
    );

    const promise = fileToBase64(mockFile);
    mockReader.onloadend();

    const result = await promise;
    expect(result).toBe(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
    );
  });

  it("should handle empty file", async () => {
    const mockFile = new File([""], "empty.txt", { type: "text/plain" });

    const mockReader = {
      result: "data:text/plain;base64,",
      onloadend: null as (() => void) | null,
      readAsDataURL: vi.fn(),
    };

    vi.spyOn(window, "FileReader").mockImplementation(
      () => mockReader as Partial<FileReader>,
    );

    const promise = fileToBase64(mockFile);
    mockReader.onloadend();

    const result = await promise;
    expect(result).toBe("");
  });

  it("should remove data URL prefix correctly", async () => {
    const mockFile = new File(["test"], "test.txt", { type: "text/plain" });

    const mockReader = {
      result: "data:text/plain;charset=utf-8;base64,dGVzdA==",
      onloadend: null as (() => void) | null,
      readAsDataURL: vi.fn(),
    };

    vi.spyOn(window, "FileReader").mockImplementation(
      () => mockReader as Partial<FileReader>,
    );

    const promise = fileToBase64(mockFile);
    mockReader.onloadend();

    const result = await promise;
    expect(result).toBe("dGVzdA==");
  });
});
