import type { Triple, Term } from "@trustgraph/client";
import { Match } from "effect";
import * as S from "effect/Schema";
import type { ForceGraphProps, NodeObject, LinkObject } from "react-force-graph-2d";

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

const GraphNodeValue: S.Codec<GraphNode, GraphNode> = S.Struct({
  id: S.String,
  label: S.String,
  color: S.optionalKey(S.String),
  degree: S.Finite,
});

const GraphLinkValue: S.Codec<GraphLink, GraphLink> = S.Struct({
  source: S.String,
  target: S.String,
  label: S.String,
});

export class GraphData extends S.Class<GraphData>("GraphData")({
  nodes: S.Array(GraphNodeValue).pipe(S.mutable),
  links: S.Array(GraphLinkValue).pipe(S.mutable),
}, { description: "Renderable graph nodes and links derived from triples." }) {}

export const DEFAULT_GRAPH_NODE_COLOR = "#82b582";

const GRAPH_NODE_PALETTE = [
  DEFAULT_GRAPH_NODE_COLOR,
  "#5c9a5c",
  "#3d7d3d",
  "#aed1ae",
  "#22c55e",
  "#eab308",
  "#a1a1aa",
  "#71717a",
];

export const directedGraphLinkProps = {
  autoPauseRedraw: false,
  linkColor: "rgba(161,161,170,0.55)",
  linkWidth: 1.4,
  linkDirectionalArrowLength: 9,
  linkDirectionalArrowRelPos: 0.58,
  linkDirectionalArrowColor: "rgba(174,209,174,0.98)",
  linkDirectionalParticles: 1,
  linkDirectionalParticleSpeed: 0.005,
  linkDirectionalParticleWidth: 2.2,
  linkDirectionalParticleColor: "rgba(92,154,92,0.95)",
} satisfies Partial<ForceGraphProps<GraphNode, GraphLink>>;

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
  const index = Math.abs(hash) % GRAPH_NODE_PALETTE.length;
  return GRAPH_NODE_PALETTE[index];
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

  const ensureNode = (uri: string): GraphNode => {
    const existing = nodeMap.get(uri);
    if (existing !== undefined) return existing;
    const type = typeMap.get(uri);
    const node: GraphNode = {
      id: uri,
      label: labelMap.get(uri) ?? localName(uri),
      color: hashColor(type !== undefined ? localName(type) : uri),
      degree: 0,
    };
    nodeMap.set(uri, node);
    return node;
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

    ensureNode(sVal).degree++;
    ensureNode(oVal).degree++;

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
