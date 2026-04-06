// ── Domain Types ─────────────────────────────────────────────────
export type DomainKey = string;

export interface EntityProps {
  [key: string]: string | number;
}

export interface Subclass {
  id: string;
  uri?: string;
  label: string;
  props: EntityProps;
}

export interface OntologyDomain {
  label: string;
  color: string;
  glow: string;
  icon: string;
  description: string;
  properties: string[];
  subclasses: Subclass[];
}

export type OntologyType = Record<DomainKey, OntologyDomain>;

// ── Relationship Types ───────────────────────────────────────────
export interface Relationship {
  from: string;
  to: string;
  predicate: string;
  strength?: number;
  domain: [DomainKey, DomainKey];
}

// ── Query Types ──────────────────────────────────────────────────
export interface DemoQuery {
  q: string;
  thinking: string[];
  answer: string;
  entities: string[];
  triples: number;
}

// ── Entity Types ─────────────────────────────────────────────────
export interface Entity extends Subclass {
  domain: DomainKey;
  color: string;
  glow: string;
  icon: string;
}

export interface GraphNode extends Entity {
  x: number;
  y: number;
  vx: number;
  vy: number;
  targetX: number;
  targetY: number;
  r: number;
}

// ── UI State Types ───────────────────────────────────────────────
export type TabKey = "graph" | "query" | "explain" | "ontology" | "data";
export type QueryPhase = "idle" | "thinking" | "answering" | "done";
