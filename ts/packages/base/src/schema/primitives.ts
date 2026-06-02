/**
 * Schema-backed core data types mirroring the Python schema primitives.
 *
 * Python reference: trustgraph-base/trustgraph/schema/core/primitives.py
 */

import * as S from "effect/Schema";

export const TgError = S.Struct({
  type: S.String,
  message: S.String,
});
export type TgError = typeof TgError.Type;

export const TermType = S.Literals([
  "IRI",
  "BLANK",
  "LITERAL",
  "TRIPLE",
]);
export type TermType = typeof TermType.Type;

export const IriTerm = S.Struct({
  type: S.tag("IRI"),
  iri: S.String,
});
export type IriTerm = typeof IriTerm.Type;

export const BlankTerm = S.Struct({
  type: S.tag("BLANK"),
  id: S.String,
});
export type BlankTerm = typeof BlankTerm.Type;

export const LiteralTerm = S.Struct({
  type: S.tag("LITERAL"),
  value: S.String,
  datatype: S.optionalKey(S.String),
  language: S.optionalKey(S.String),
});
export type LiteralTerm = typeof LiteralTerm.Type;

export type Term = IriTerm | BlankTerm | LiteralTerm | TripleTerm;
export type Triple = {
  readonly s: Term;
  readonly p: Term;
  readonly o: Term;
  readonly g?: string;
};

export const Triple: S.Codec<Triple, Triple> = S.Struct({
  s: S.suspend((): S.Codec<Term, Term> => Term),
  p: S.suspend((): S.Codec<Term, Term> => Term),
  o: S.suspend((): S.Codec<Term, Term> => Term),
  g: S.optionalKey(S.String),
});

export const TripleTerm: S.Codec<TripleTerm, TripleTerm> = S.Struct({
  type: S.tag("TRIPLE"),
  triple: S.suspend((): S.Codec<Triple, Triple> => Triple),
});
export interface TripleTerm {
  readonly type: "TRIPLE";
  readonly triple: Triple;
}

export const Term = S.Union([IriTerm, BlankTerm, LiteralTerm, TripleTerm]).pipe(
  S.toTaggedUnion("type"),
);

export const Field = S.Struct({
  name: S.String,
  type: S.String,
  description: S.optionalKey(S.String),
});
export type Field = typeof Field.Type;

export const RowSchema = S.Struct({
  name: S.String,
  description: S.optionalKey(S.String),
  fields: S.Array(Field).pipe(S.mutable),
});
export type RowSchema = typeof RowSchema.Type;

export const LlmResult = S.Struct({
  text: S.String,
  inToken: S.Number,
  outToken: S.Number,
  model: S.String,
});
export type LlmResult = typeof LlmResult.Type;

export const LlmChunk = S.Struct({
  text: S.String,
  inToken: S.NullOr(S.Number),
  outToken: S.NullOr(S.Number),
  model: S.String,
  isFinal: S.Boolean,
});
export type LlmChunk = typeof LlmChunk.Type;
