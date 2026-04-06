/**
 * Collection manager — in-memory CRUD for document collections.
 *
 * Used by LibrarianService to manage collections per-user.
 * MVP: purely in-memory, no persistence (state is persisted
 * via the parent LibrarianService JSON snapshot).
 */

export interface CollectionEntry {
  user: string;
  collection: string;
  name: string;
  description: string;
  tags: string[];
}

export class CollectionManager {
  /** keyed by `${user}:${collection}` */
  private collections = new Map<string, CollectionEntry>();

  private key(user: string, collection: string): string {
    return `${user}:${collection}`;
  }

  listCollections(user: string): CollectionEntry[] {
    const result: CollectionEntry[] = [];
    for (const entry of this.collections.values()) {
      if (entry.user === user) {
        result.push(entry);
      }
    }
    return result;
  }

  getCollection(user: string, collection: string): CollectionEntry | undefined {
    return this.collections.get(this.key(user, collection));
  }

  updateCollection(
    user: string,
    collection: string,
    name: string,
    description: string,
    tags: string[],
  ): CollectionEntry {
    const entry: CollectionEntry = { user, collection, name, description, tags };
    this.collections.set(this.key(user, collection), entry);
    return entry;
  }

  deleteCollection(user: string, collection: string): boolean {
    return this.collections.delete(this.key(user, collection));
  }

  ensureCollectionExists(user: string, collection: string): CollectionEntry {
    const existing = this.getCollection(user, collection);
    if (existing) return existing;
    return this.updateCollection(user, collection, collection, "", []);
  }

  /** Serialize to a plain array for JSON persistence. */
  toJSON(): CollectionEntry[] {
    return [...this.collections.values()];
  }

  /** Restore from a serialized array. */
  loadFromJSON(entries: CollectionEntry[]): void {
    this.collections.clear();
    for (const entry of entries) {
      this.collections.set(this.key(entry.user, entry.collection), entry);
    }
  }
}
