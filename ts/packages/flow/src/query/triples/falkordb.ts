/**
 * FalkorDB triples query service — queries RDF triples from FalkorDB.
 *
 * Implements all SPO query patterns (S, P, O, SP, SO, PO, SPO, *).
 *
 * Python reference: trustgraph-flow/trustgraph/query/triples/falkordb/service.py
 */

import { createClient, Graph } from "falkordb";
import type { Term, Triple } from "@trustgraph/base";

export interface FalkorDBQueryConfig {
  url?: string;
  database?: string;
}

function termToValue(term: Term | undefined): string | null {
  if (term === undefined) return null;
  switch (term.type) {
    case "IRI": return term.iri;
    case "LITERAL": return term.value;
    case "BLANK": return term.id;
    default: return null;
  }
}

function createTerm(value: string): Term {
  if (value.length === 0) {
    return { type: "LITERAL", value: "" };
  }
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return { type: "IRI", iri: value };
  }
  return { type: "LITERAL", value };
}

/** Extract a string field from a FalkorDB result row (returns object with named keys). */
function field(row: unknown, key: string): string {
  return (row as Record<string, unknown>)?.[key] as string ?? "";
}

export class FalkorDBTriplesQuery {
  private graph: Graph;
  private connectPromise: Promise<void>;

  constructor(config: FalkorDBQueryConfig = {}) {
    const url = config.url ?? process.env.FALKORDB_URL ?? "redis://localhost:6379";
    const database = config.database ?? "falkordb";

    const client = createClient({ url });
    this.graph = new Graph(client, database);
    this.connectPromise = client.connect().then(() => {
      console.log(`[FalkorDBTriplesQuery] Connected to ${url}, graph: ${database}`);
    }).catch((err) => {
      console.error(`[FalkorDBTriplesQuery] Connection failed:`, err);
      throw err;
    });
  }

  private async ensureConnected(): Promise<void> {
    await this.connectPromise;
  }

  async queryTriples(
    s?: Term,
    p?: Term,
    o?: Term,
    limit = 100,
  ): Promise<Triple[]> {
    await this.ensureConnected();
    const sv = termToValue(s);
    const pv = termToValue(p);
    const ov = termToValue(o);

    const rawTriples: [string, string, string][] = [];

    // Query both Node and Literal targets for each pattern
    if (sv !== null && pv !== null && ov !== null) {
      // SPO — exact match
      await this.matchPattern(rawTriples, sv, pv, ov, limit);
    } else if (sv !== null && pv !== null) {
      // SP — known subject + predicate
      await this.matchSP(rawTriples, sv, pv, limit);
    } else if (sv !== null && ov !== null) {
      // SO — known subject + object
      await this.matchSO(rawTriples, sv, ov, limit);
    } else if (pv !== null && ov !== null) {
      // PO — known predicate + object
      await this.matchPO(rawTriples, pv, ov, limit);
    } else if (sv !== null) {
      // S only
      await this.matchS(rawTriples, sv, limit);
    } else if (pv !== null) {
      // P only
      await this.matchP(rawTriples, pv, limit);
    } else if (ov !== null) {
      // O only
      await this.matchO(rawTriples, ov, limit);
    } else {
      // Wildcard — all triples
      await this.matchAll(rawTriples, limit);
    }

    return rawTriples
      .filter(([s, p, o]) => s !== null && p !== null && o !== null)
      .slice(0, limit)
      .map(([s, p, o]) => ({
        s: createTerm(s),
        p: createTerm(p),
        o: createTerm(o),
      }));
  }

  private async matchPattern(
    out: [string, string, string][],
    sv: string, pv: string, ov: string, limit: number,
  ): Promise<void> {
    for (const destType of ["Literal", "Node"] as const) {
      const destKey = destType === "Literal" ? "value" : "uri";
      const result = await this.graph.query(
        `MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:${destType} {${destKey}: $dest}) ` +
        `RETURN src.uri LIMIT ${limit}`,
        { params: { src: sv, rel: pv, dest: ov } },
      );
      for (const _rec of (result.data ?? [])) {
        out.push([sv, pv, ov]);
      }
    }
  }

  private async matchSP(
    out: [string, string, string][],
    sv: string, pv: string, limit: number,
  ): Promise<void> {
    // Literals
    const litResult = await this.graph.query(
      `MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Literal) ` +
      `RETURN dest.value as dest LIMIT ${limit}`,
      { params: { src: sv, rel: pv } },
    );
    for (const rec of (litResult.data ?? [])) {
      out.push([sv, pv, field(rec, "dest")]);
    }
    // Nodes
    const nodeResult = await this.graph.query(
      `MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Node) ` +
      `RETURN dest.uri as dest LIMIT ${limit}`,
      { params: { src: sv, rel: pv } },
    );
    for (const rec of (nodeResult.data ?? [])) {
      out.push([sv, pv, field(rec, "dest")]);
    }
  }

  private async matchSO(
    out: [string, string, string][],
    sv: string, ov: string, limit: number,
  ): Promise<void> {
    for (const [destType, destKey] of [["Literal", "value"], ["Node", "uri"]] as const) {
      const result = await this.graph.query(
        `MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:${destType} {${destKey}: $dest}) ` +
        `RETURN rel.uri as rel LIMIT ${limit}`,
        { params: { src: sv, dest: ov } },
      );
      for (const rec of (result.data ?? [])) {
        out.push([sv, field(rec, "rel"), ov]);
      }
    }
  }

  private async matchPO(
    out: [string, string, string][],
    pv: string, ov: string, limit: number,
  ): Promise<void> {
    for (const [destType, destKey] of [["Literal", "value"], ["Node", "uri"]] as const) {
      const result = await this.graph.query(
        `MATCH (src:Node)-[rel:Rel {uri: $rel}]->(dest:${destType} {${destKey}: $dest}) ` +
        `RETURN src.uri as src LIMIT ${limit}`,
        { params: { rel: pv, dest: ov } },
      );
      for (const rec of (result.data ?? [])) {
        out.push([field(rec, "src"), pv, ov]);
      }
    }
  }

  private async matchS(
    out: [string, string, string][],
    sv: string, limit: number,
  ): Promise<void> {
    const litResult = await this.graph.query(
      `MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Literal) ` +
      `RETURN rel.uri as rel, dest.value as dest LIMIT ${limit}`,
      { params: { src: sv } },
    );
    for (const rec of (litResult.data ?? [])) {
      out.push([sv, field(rec, "rel"), field(rec, "dest")]);
    }
    const nodeResult = await this.graph.query(
      `MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Node) ` +
      `RETURN rel.uri as rel, dest.uri as dest LIMIT ${limit}`,
      { params: { src: sv } },
    );
    for (const rec of (nodeResult.data ?? [])) {
      out.push([sv, field(rec, "rel"), field(rec, "dest")]);
    }
  }

  private async matchP(
    out: [string, string, string][],
    pv: string, limit: number,
  ): Promise<void> {
    const litResult = await this.graph.query(
      `MATCH (src:Node)-[rel:Rel {uri: $rel}]->(dest:Literal) ` +
      `RETURN src.uri as src, dest.value as dest LIMIT ${limit}`,
      { params: { rel: pv } },
    );
    for (const rec of (litResult.data ?? [])) {
      out.push([field(rec, "src"), pv, field(rec, "dest")]);
    }
    const nodeResult = await this.graph.query(
      `MATCH (src:Node)-[rel:Rel {uri: $rel}]->(dest:Node) ` +
      `RETURN src.uri as src, dest.uri as dest LIMIT ${limit}`,
      { params: { rel: pv } },
    );
    for (const rec of (nodeResult.data ?? [])) {
      out.push([field(rec, "src"), pv, field(rec, "dest")]);
    }
  }

  private async matchO(
    out: [string, string, string][],
    ov: string, limit: number,
  ): Promise<void> {
    for (const [destType, destKey] of [["Literal", "value"], ["Node", "uri"]] as const) {
      const result = await this.graph.query(
        `MATCH (src:Node)-[rel:Rel]->(dest:${destType} {${destKey}: $dest}) ` +
        `RETURN src.uri as src, rel.uri as rel LIMIT ${limit}`,
        { params: { dest: ov } },
      );
      for (const rec of (result.data ?? [])) {
        out.push([field(rec, "src"), field(rec, "rel"), ov]);
      }
    }
  }

  private async matchAll(
    out: [string, string, string][],
    limit: number,
  ): Promise<void> {
    const litResult = await this.graph.query(
      `MATCH (src:Node)-[rel:Rel]->(dest:Literal) ` +
      `RETURN src.uri as src, rel.uri as rel, dest.value as dest LIMIT ${limit}`,
    );
    for (const rec of (litResult.data ?? [])) {
      out.push([field(rec, "src"), field(rec, "rel"), field(rec, "dest")]);
    }
    const nodeResult = await this.graph.query(
      `MATCH (src:Node)-[rel:Rel]->(dest:Node) ` +
      `RETURN src.uri as src, rel.uri as rel, dest.uri as dest LIMIT ${limit}`,
    );
    for (const rec of (nodeResult.data ?? [])) {
      out.push([field(rec, "src"), field(rec, "rel"), field(rec, "dest")]);
    }
  }
}
