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

export interface CollectionManager {
  readonly listCollections: (user: string) => CollectionEntry[];
  readonly getCollection: (user: string, collection: string) => CollectionEntry | undefined;
  readonly updateCollection: (
    user: string,
    collection: string,
    name: string,
    description: string,
    tags: string[],
  ) => CollectionEntry;
  readonly deleteCollection: (user: string, collection: string) => boolean;
  readonly ensureCollectionExists: (user: string, collection: string) => CollectionEntry;
  readonly toJSON: () => CollectionEntry[];
  readonly loadFromJSON: (entries: CollectionEntry[]) => void;
}

export function makeCollectionManager(): CollectionManager {
  /** keyed by `${user}:${collection}` */
  const collections = new Map<string, CollectionEntry>();

  const key = (user: string, collection: string): string => `${user}:${collection}`;

  const updateCollection = (
    user: string,
    collection: string,
    name: string,
    description: string,
    tags: string[],
  ): CollectionEntry => {
    const entry: CollectionEntry = { user, collection, name, description, tags };
    collections.set(key(user, collection), entry);
    return entry;
  };

  return {
    listCollections: (user) => {
      const result: CollectionEntry[] = [];
      for (const entry of collections.values()) {
        if (entry.user === user) {
          result.push(entry);
        }
      }
      return result;
    },
    getCollection: (user, collection) => collections.get(key(user, collection)),
    updateCollection,
    deleteCollection: (user, collection) => collections.delete(key(user, collection)),
    ensureCollectionExists: (user, collection) => {
      const existing = collections.get(key(user, collection));
      if (existing !== undefined) return existing;
      return updateCollection(user, collection, collection, "", []);
    },
    /** Serialize to a plain array for JSON persistence. */
    toJSON: () => [...collections.values()],
    /** Restore from a serialized array. */
    loadFromJSON: (entries) => {
      collections.clear();
      for (const entry of entries) {
        collections.set(key(entry.user, entry.collection), entry);
      }
    },
  };
}
