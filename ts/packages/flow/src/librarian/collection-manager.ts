/**
 * Collection manager — in-memory CRUD for document collections.
 *
 * Used by LibrarianService to manage collections per-user.
 * MVP: purely in-memory, no persistence (state is persisted
 * via the parent LibrarianService JSON snapshot).
 */

import * as MutableHashMap from "effect/MutableHashMap";
import * as O from "effect/Option";

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
  const collections = MutableHashMap.empty<string, CollectionEntry>();

  const key = (user: string, collection: string): string => `${user}:${collection}`;

  const updateCollection = (
    user: string,
    collection: string,
    name: string,
    description: string,
    tags: string[],
  ): CollectionEntry => {
    const entry: CollectionEntry = { user, collection, name, description, tags };
    MutableHashMap.set(collections, key(user, collection), entry);
    return entry;
  };

  return {
    listCollections: (user) => {
      const result: CollectionEntry[] = [];
      for (const entry of MutableHashMap.values(collections)) {
        if (entry.user === user) {
          result.push(entry);
        }
      }
      return result;
    },
    getCollection: (user, collection) =>
      O.getOrUndefined(MutableHashMap.get(collections, key(user, collection))),
    updateCollection,
    deleteCollection: (user, collection) => {
      const collectionKey = key(user, collection);
      const exists = MutableHashMap.has(collections, collectionKey);
      MutableHashMap.remove(collections, collectionKey);
      return exists;
    },
    ensureCollectionExists: (user, collection) => {
      const existing = O.getOrUndefined(MutableHashMap.get(collections, key(user, collection)));
      if (existing !== undefined) return existing;
      return updateCollection(user, collection, collection, "", []);
    },
    /** Serialize to a plain array for JSON persistence. */
    toJSON: () => Array.from(MutableHashMap.values(collections)),
    /** Restore from a serialized array. */
    loadFromJSON: (entries) => {
      MutableHashMap.clear(collections);
      for (const entry of entries) {
        MutableHashMap.set(collections, key(entry.user, entry.collection), entry);
      }
    },
  };
}
