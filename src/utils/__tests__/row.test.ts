import { describe, it, expect, vi } from "vitest";
import { computeCosineSimilarity, sortSimilarity, type Row } from "../row";

// Mock the compute-cosine-similarity package
vi.mock("compute-cosine-similarity", () => ({
  default: vi.fn(),
}));

import similarity from "compute-cosine-similarity";

describe("computeCosineSimilarity", () => {
  it("should compute cosine similarity for entities with embeddings", () => {
    const mockSimilarity = vi.mocked(similarity);
    mockSimilarity.mockReturnValue(0.8);

    const entities: Row[] = [
      {
        uri: "http://example.com/entity1",
        label: "Entity 1",
        description: "Description 1",
        embeddings: [0.1, 0.2, 0.3],
        target: [0.2, 0.3, 0.4],
      },
      {
        uri: "http://example.com/entity2",
        label: "Entity 2",
        description: "Description 2",
        embeddings: [0.4, 0.5, 0.6],
        target: [0.5, 0.6, 0.7],
      },
    ];

    const result = computeCosineSimilarity()(entities);

    expect(result).toHaveLength(2);
    expect(result[0]).toEqual({
      uri: "http://example.com/entity1",
      label: "Entity 1",
      description: "Description 1",
      similarity: 0.8,
    });
    expect(result[1]).toEqual({
      uri: "http://example.com/entity2",
      label: "Entity 2",
      description: "Description 2",
      similarity: 0.8,
    });

    expect(mockSimilarity).toHaveBeenCalledWith(
      [0.2, 0.3, 0.4],
      [0.1, 0.2, 0.3],
    );
    expect(mockSimilarity).toHaveBeenCalledWith(
      [0.5, 0.6, 0.7],
      [0.4, 0.5, 0.6],
    );
  });

  it("should handle null similarity result", () => {
    const mockSimilarity = vi.mocked(similarity);
    mockSimilarity.mockReturnValue(null);

    const entities: Row[] = [
      {
        uri: "http://example.com/entity1",
        label: "Entity 1",
        embeddings: [0.1, 0.2, 0.3],
        target: [0.2, 0.3, 0.4],
      },
    ];

    const result = computeCosineSimilarity()(entities);

    expect(result[0].similarity).toBe(-1);
  });

  it("should handle empty entities array", () => {
    const result = computeCosineSimilarity()([]);
    expect(result).toEqual([]);
  });

  it("should preserve original entity data except embeddings and target", () => {
    const mockSimilarity = vi.mocked(similarity);
    mockSimilarity.mockReturnValue(0.5);

    const entities: Row[] = [
      {
        uri: "http://example.com/entity1",
        label: "Entity 1",
        description: "Description 1",
        embeddings: [0.1, 0.2, 0.3],
        target: [0.2, 0.3, 0.4],
      },
    ];

    const result = computeCosineSimilarity()(entities);

    expect(result[0]).not.toHaveProperty("embeddings");
    expect(result[0]).not.toHaveProperty("target");
    expect(result[0]).toHaveProperty("uri");
    expect(result[0]).toHaveProperty("label");
    expect(result[0]).toHaveProperty("description");
    expect(result[0]).toHaveProperty("similarity");
  });
});

describe("sortSimilarity", () => {
  it("should sort entities by similarity in descending order", () => {
    const entities: Row[] = [
      { uri: "entity1", similarity: 0.3 },
      { uri: "entity2", similarity: 0.9 },
      { uri: "entity3", similarity: 0.6 },
    ];

    const result = sortSimilarity()(entities);

    expect(result[0].similarity).toBe(0.9);
    expect(result[1].similarity).toBe(0.6);
    expect(result[2].similarity).toBe(0.3);
  });

  it("should handle entities with same similarity", () => {
    const entities: Row[] = [
      { uri: "entity1", similarity: 0.5 },
      { uri: "entity2", similarity: 0.5 },
      { uri: "entity3", similarity: 0.7 },
    ];

    const result = sortSimilarity()(entities);

    expect(result[0].similarity).toBe(0.7);
    expect(result[1].similarity).toBe(0.5);
    expect(result[2].similarity).toBe(0.5);
  });

  it("should handle empty array", () => {
    const result = sortSimilarity()([]);
    expect(result).toEqual([]);
  });

  it("should handle single entity", () => {
    const entities: Row[] = [{ uri: "entity1", similarity: 0.5 }];

    const result = sortSimilarity()(entities);
    expect(result).toEqual(entities);
  });

  it("should not mutate original array", () => {
    const entities: Row[] = [
      { uri: "entity1", similarity: 0.3 },
      { uri: "entity2", similarity: 0.9 },
    ];
    const originalOrder = [...entities];

    sortSimilarity()(entities);

    expect(entities).toEqual(originalOrder);
  });

  it("should handle negative similarities", () => {
    const entities: Row[] = [
      { uri: "entity1", similarity: -0.5 },
      { uri: "entity2", similarity: 0.2 },
      { uri: "entity3", similarity: -0.1 },
    ];

    const result = sortSimilarity()(entities);

    expect(result[0].similarity).toBe(0.2);
    expect(result[1].similarity).toBe(-0.1);
    expect(result[2].similarity).toBe(-0.5);
  });
});
