import { describe, expect, it } from "vitest";
import { makeCollectionManager } from "../librarian/collection-manager.js";

describe("CollectionManager", () => {
  it("manages collection entries through Effect MutableHashMap state", () => {
    const manager = makeCollectionManager();

    const created = manager.ensureCollectionExists("alice", "papers");
    expect(created).toEqual({
      user: "alice",
      collection: "papers",
      name: "papers",
      description: "",
      tags: [],
    });

    const updated = manager.updateCollection(
      "alice",
      "papers",
      "Research Papers",
      "Curated PDFs",
      ["research", "pdf"],
    );
    manager.updateCollection("bob", "notes", "Notes", "", []);

    expect(manager.getCollection("alice", "papers")).toEqual(updated);
    expect(manager.listCollections("alice")).toEqual([updated]);
    expect(manager.toJSON()).toEqual([updated, {
      user: "bob",
      collection: "notes",
      name: "Notes",
      description: "",
      tags: [],
    }]);

    expect(manager.deleteCollection("alice", "papers")).toBe(true);
    expect(manager.deleteCollection("alice", "papers")).toBe(false);
    expect(manager.getCollection("alice", "papers")).toBeUndefined();

    manager.loadFromJSON([updated]);
    expect(manager.listCollections("alice")).toEqual([updated]);
    expect(manager.listCollections("bob")).toEqual([]);
  });
});
