/**
 * Core data types mirroring the Python schema primitives.
 *
 * Python reference: trustgraph-base/trustgraph/schema/core/primitives.py
 */

export interface TgError {
  type: string;
  message: string;
}

// RDF Term types — discriminated union
export type TermType = "IRI" | "BLANK" | "LITERAL" | "TRIPLE";

export interface IriTerm {
  type: "IRI";
  iri: string;
}

export interface BlankTerm {
  type: "BLANK";
  id: string;
}

export interface LiteralTerm {
  type: "LITERAL";
  value: string;
  datatype?: string;
  language?: string;
}

export interface TripleTerm {
  type: "TRIPLE";
  triple: Triple;
}

export type Term = IriTerm | BlankTerm | LiteralTerm | TripleTerm;

export interface Triple {
  s: Term;
  p: Term;
  o: Term;
  g?: Term; // Named graph (optional quad)
}

export interface Field {
  name: string;
  type: string;
  description?: string;
}

export interface RowSchema {
  name: string;
  description?: string;
  fields: Field[];
}

// LLM-related types
export interface LlmResult {
  text: string;
  inToken: number;
  outToken: number;
  model: string;
}

export interface LlmChunk {
  text: string;
  inToken: number | null;
  outToken: number | null;
  model: string;
  isFinal: boolean;
}
