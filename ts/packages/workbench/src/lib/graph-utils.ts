import type { Triple, Term } from "@trustgraph/client";
import { Match } from "effect";
import type { NodeObject, LinkObject } from "react-force-graph-2d";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

export const RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label";
export const RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface GraphNode extends NodeObject {
  id: string;
  label: string;
  color?: string;
  /** Number of connections (used for sizing) */
  degree: number;
}

export interface GraphLink extends LinkObject {
  source: string;
  target: string;
  label: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

// ---------------------------------------------------------------------------
// Term helpers
// ---------------------------------------------------------------------------

export function termValue(t: Term): string {
  return Match.type<Term>().pipe(
    Match.discriminatorsExhaustive("t")({
      i: (iri) => iri.i,
      l: (literal) => literal.v,
      b: (blank) => blank.d,
      t: () => "[triple]",
    }),
  )(t);
}

export function isIri(t: Term): boolean {
  return t.t === "i";
}

/** Extract the local name from a URI for display */
export function localName(uri: string): string {
  const hash = uri.lastIndexOf("#");
  const slash = uri.lastIndexOf("/");
  const idx = Math.max(hash, slash);
  if (idx >= 0 && idx < uri.length - 1) return uri.substring(idx + 1);
  return uri;
}

/** Deterministic color from a string (for node types) */
export function hashColor(s: string): string {
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = s.charCodeAt(i) + ((hash << 5) - hash);
  }
  const hue = ((hash % 360) + 360) % 360;
  return `hsl(${hue}, 60%, 55%)`;
}

// ---------------------------------------------------------------------------
// Build graph data from triples
// ---------------------------------------------------------------------------

export function triplesToGraph(triples: Triple[]): {
  data: GraphData;
  labelMap: Map<string, string>;
  typeMap: Map<string, string>;
} {
  const labelMap = new Map<string, string>();
  const typeMap = new Map<string, string>();

  // First pass: collect labels and types
  for (const t of triples) {
    const pred = termValue(t.p);
    if (pred === RDFS_LABEL && t.o.t === "l") {
      labelMap.set(termValue(t.s), t.o.v);
    }
    if (pred === RDF_TYPE && isIri(t.o)) {
      typeMap.set(termValue(t.s), termValue(t.o));
    }
  }

  // Second pass: build nodes and links (skip structural triples)
  const nodeMap = new Map<string, GraphNode>();
  const links: GraphLink[] = [];

  const ensureNode = (uri: string): void => {
    if (!nodeMap.has(uri)) {
      const type = typeMap.get(uri);
      nodeMap.set(uri, {
        id: uri,
        label: labelMap.get(uri) ?? localName(uri),
        color: type !== undefined ? hashColor(localName(type)) : "#5b80ff",
        degree: 0,
      });
    }
  };

  for (const t of triples) {
    const sVal = termValue(t.s);
    const pVal = termValue(t.p);
    const oVal = termValue(t.o);

    // Skip label and type predicates -- they are metadata, not graph edges
    if (pVal === RDFS_LABEL) continue;
    if (pVal === RDF_TYPE) continue;

    // Build edges for entity-to-entity relationships.
    // Include both IRIs and literals as valid entity nodes — plain-name
    // knowledge graphs (e.g. seeded demo data) use literals for entities.
    const sIsEntity = isIri(t.s) || t.s.t === "l";
    const oIsEntity = isIri(t.o) || t.o.t === "l";
    if (!sIsEntity || !oIsEntity) continue;

    ensureNode(sVal);
    ensureNode(oVal);
    nodeMap.get(sVal)!.degree++;
    nodeMap.get(oVal)!.degree++;

    links.push({
      source: sVal,
      target: oVal,
      label: labelMap.get(pVal) ?? localName(pVal),
    });
  }

  return {
    data: { nodes: Array.from(nodeMap.values()), links },
    labelMap,
    typeMap,
  };
}
