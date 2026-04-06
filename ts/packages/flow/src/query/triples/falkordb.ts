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
  if (!term) return null;
  switch (term.type) {
    case "IRI": return term.iri;
    case "LITERAL": return term.value;
    case "BLANK": return term.id;
    default: return null;
  }
}

function createTerm(value: string): Term {
  if (value.startsWith("http://") || value.startsWith("https://")) {
    return { type: "IRI", iri: value };
  }
  return { type: "LITERAL", value };
}

export class FalkorDBTriplesQuery {
  private graph: Graph;

  constructor(config: FalkorDBQueryConfig = {}) {
    const url = config.url ?? process.env.FALKORDB_URL ?? "redis://localhost:6379";
    const database = config.database ?? "falkordb";

    const client = createClient({ url });
    this.graph = new Graph(client, database);
  }

  async queryTriples(
    s?: Term,
    p?: Term,
    o?: Term,
    limit = 100,
  ): Promise<Triple[]> {
    const sv = termToValue(s);
    const pv = termToValue(p);
    const ov = termToValue(o);

    const rawTriples: [string, string, string][] = [];

    // Query both Node and Literal targets for each pattern
    if (sv && pv && ov) {
      // SPO — exact match
      await this.matchPattern(rawTriples, sv, pv, ov, limit);
    } else if (sv && pv) {
      // SP — known subject + predicate
      await this.matchSP(rawTriples, sv, pv, limit);
    } else if (sv && ov) {
      // SO — known subject + object
      await this.matchSO(rawTriples, sv, ov, limit);
    } else if (pv && ov) {
      // PO — known predicate + object
      await this.matchPO(rawTriples, pv, ov, limit);
    } else if (sv) {
      // S only
      await this.matchS(rawTriples, sv, limit);
    } else if (pv) {
      // P only
      await this.matchP(rawTriples, pv, limit);
    } else if (ov) {
      // O only
      await this.matchO(rawTriples, ov, limit);
    } else {
      // Wildcard — all triples
      await this.matchAll(rawTriples, limit);
    }

    return rawTriples.slice(0, limit).map(([s, p, o]) => ({
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
      for (const _rec of (result.data ?? []) as unknown[][]) {
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
    for (const rec of (litResult.data ?? []) as string[][]) {
      out.push([sv, pv, rec[0] as string]);
    }
    // Nodes
    const nodeResult = await this.graph.query(
      `MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Node) ` +
      `RETURN dest.uri as dest LIMIT ${limit}`,
      { params: { src: sv, rel: pv } },
    );
    for (const rec of (nodeResult.data ?? []) as string[][]) {
      out.push([sv, pv, rec[0] as string]);
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
      for (const rec of (result.data ?? []) as string[][]) {
        out.push([sv, rec[0] as string, ov]);
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
      for (const rec of (result.data ?? []) as string[][]) {
        out.push([rec[0] as string, pv, ov]);
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
    for (const rec of (litResult.data ?? []) as string[][]) {
      out.push([sv, rec[0] as string, rec[1] as string]);
    }
    const nodeResult = await this.graph.query(
      `MATCH (src:Node {uri: $src})-[rel:Rel]->(dest:Node) ` +
      `RETURN rel.uri as rel, dest.uri as dest LIMIT ${limit}`,
      { params: { src: sv } },
    );
    for (const rec of (nodeResult.data ?? []) as string[][]) {
      out.push([sv, rec[0] as string, rec[1] as string]);
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
    for (const rec of (litResult.data ?? []) as string[][]) {
      out.push([rec[0] as string, pv, rec[1] as string]);
    }
    const nodeResult = await this.graph.query(
      `MATCH (src:Node)-[rel:Rel {uri: $rel}]->(dest:Node) ` +
      `RETURN src.uri as src, dest.uri as dest LIMIT ${limit}`,
      { params: { rel: pv } },
    );
    for (const rec of (nodeResult.data ?? []) as string[][]) {
      out.push([rec[0] as string, pv, rec[1] as string]);
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
      for (const rec of (result.data ?? []) as string[][]) {
        out.push([rec[0] as string, rec[1] as string, ov]);
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
    for (const rec of (litResult.data ?? []) as string[][]) {
      out.push([rec[0] as string, rec[1] as string, rec[2] as string]);
    }
    const nodeResult = await this.graph.query(
      `MATCH (src:Node)-[rel:Rel]->(dest:Node) ` +
      `RETURN src.uri as src, rel.uri as rel, dest.uri as dest LIMIT ${limit}`,
    );
    for (const rec of (nodeResult.data ?? []) as string[][]) {
      out.push([rec[0] as string, rec[1] as string, rec[2] as string]);
    }
  }
}
