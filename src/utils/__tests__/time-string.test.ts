import { describe, it, expect, vi, beforeEach } from "vitest";
import { timeString } from "../time-string";

describe("timeString", () => {
  beforeEach(() => {
    // Mock Date to ensure consistent testing
    vi.setSystemTime(new Date("2024-01-15T12:00:00Z"));
  });

  it("should convert Unix timestamp to localized date and time string", () => {
    const timestamp = 1705320000; // 2024-01-15T12:00:00Z
    const result = timeString(timestamp);

    // Result should contain date and time parts
    expect(result).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}/);
    expect(result).toMatch(/\d{1,2}:\d{2}:\d{2}/);
    expect(result).toContain(" ");
  });

  it("should handle zero timestamp", () => {
    const result = timeString(0);
    expect(result).toMatch(/1970/);
  });

  it("should handle negative timestamp", () => {
    const result = timeString(-86400); // One day before epoch
    expect(result).toMatch(/1969/);
  });

  it("should handle large timestamp", () => {
    const timestamp = 2147483647; // Max 32-bit signed integer
    const result = timeString(timestamp);
    expect(result).toMatch(/2038/);
  });

  it("should return string format", () => {
    const result = timeString(1705320000);
    expect(typeof result).toBe("string");
  });
});
