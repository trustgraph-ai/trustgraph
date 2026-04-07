/**
 * FalkorDB triples store — writes RDF triples to a FalkorDB graph.
 *
 * FalkorDB is Redis-based and uses Cypher queries, same as the Python impl.
 * Pairs well with Graphiti which also uses FalkorDB as its backend.
 *
 * Python reference: trustgraph-flow/trustgraph/storage/triples/falkordb/write.py
 */

import { createClient, Graph } from "falkordb";
import type { Term, Triple } from "@trustgraph/base";

export interface FalkorDBConfig {
  url?: string;
  database?: string;
}

function getTermValue(term: Term): string {
  switch (term.type) {
    case "IRI":
      return term.iri;
    case "LITERAL":
      return term.value;
    case "BLANK":
      return term.id;
    case "TRIPLE":
      return getTermValue(term.triple.s); // fallback
  }
}

export class FalkorDBTriplesStore {
  private graph: Graph;
  private connectPromise: Promise<void>;

  constructor(config: FalkorDBConfig = {}) {
    const url = config.url ?? process.env.FALKORDB_URL ?? "redis://localhost:6379";
    const database = config.database ?? "falkordb";

    const client = createClient({ url });
    this.graph = new Graph(client, database);
    this.connectPromise = client.connect().then(() => {
      console.log(`[FalkorDBTriplesStore] Connected to ${url}, graph: ${database}`);
    }).catch((err) => {
      console.error(`[FalkorDBTriplesStore] Connection failed:`, err);
      throw err;
    });
  }

  private async ensureConnected(): Promise<void> {
    await this.connectPromise;
  }

  async createNode(uri: string, user: string, collection: string): Promise<void> {
    await this.ensureConnected();
    await this.graph.query(
      "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
      { params: { uri, user, collection } },
    );
  }

  async createLiteral(value: string, user: string, collection: string): Promise<void> {
    await this.ensureConnected();
    await this.graph.query(
      "MERGE (n:Literal {value: $value, user: $user, collection: $collection})",
      { params: { value, user, collection } },
    );
  }

  async relateNode(
    src: string, uri: string, dest: string,
    user: string, collection: string,
  ): Promise<void> {
    await this.ensureConnected();
    await this.graph.query(
      "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) " +
      "MATCH (dest:Node {uri: $dest, user: $user, collection: $collection}) " +
      "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
      { params: { src, dest, uri, user, collection } },
    );
  }

  async relateLiteral(
    src: string, uri: string, dest: string,
    user: string, collection: string,
  ): Promise<void> {
    await this.ensureConnected();
    await this.graph.query(
      "MATCH (src:Node {uri: $src, user: $user, collection: $collection}) " +
      "MATCH (dest:Literal {value: $dest, user: $user, collection: $collection}) " +
      "MERGE (src)-[:Rel {uri: $uri, user: $user, collection: $collection}]->(dest)",
      { params: { src, dest, uri, user, collection } },
    );
  }

  async storeTriples(
    triples: Triple[],
    user = "default",
    collection = "default",
  ): Promise<void> {
    for (const t of triples) {
      const s = getTermValue(t.s);
      const p = getTermValue(t.p);
      const o = getTermValue(t.o);

      await this.createNode(s, user, collection);

      if (t.o.type === "IRI") {
        await this.createNode(o, user, collection);
        await this.relateNode(s, p, o, user, collection);
      } else {
        await this.createLiteral(o, user, collection);
        await this.relateLiteral(s, p, o, user, collection);
      }
    }
  }

  async deleteCollection(user: string, collection: string): Promise<void> {
    await this.ensureConnected();
    await this.graph.query(
      "MATCH (n:Node {user: $user, collection: $collection}) DETACH DELETE n",
      { params: { user, collection } },
    );
    await this.graph.query(
      "MATCH (n:Literal {user: $user, collection: $collection}) DETACH DELETE n",
      { params: { user, collection } },
    );
    await this.graph.query(
      "MATCH (c:CollectionMetadata {user: $user, collection: $collection}) DELETE c",
      { params: { user, collection } },
    );
  }
}
