import { Schema as S } from "effect";

// Term type discriminators matching the wire format
// i = IRI, b = BLANK node, l = LITERAL, t = TRIPLE (reified)
export type TermType = "i" | "b" | "l" | "t";

export class IriTerm extends S.Class<IriTerm>("IriTerm")({
  t: S.Literal("i"),
  i: S.String,
}, { description: "IRI term in TrustGraph wire triples." }) {}

export class BlankTerm extends S.Class<BlankTerm>("BlankTerm")({
  t: S.Literal("b"),
  d: S.String,
}, { description: "Blank-node term in TrustGraph wire triples." }) {}

export class LiteralTerm extends S.Class<LiteralTerm>("LiteralTerm")({
  t: S.Literal("l"),
  v: S.String,
  dt: S.optionalKey(S.String),
  ln: S.optionalKey(S.String),
}, { description: "Literal term in TrustGraph wire triples." }) {}

export class TripleTerm extends S.Class<TripleTerm>("TripleTerm")({
  t: S.Literal("t"),
  tr: S.optionalKey(S.suspend((): S.Codec<Triple, Triple> => Triple)),
}, { description: "Reified triple term in TrustGraph wire triples." }) {}

export const Term = S.Union([IriTerm, BlankTerm, LiteralTerm, TripleTerm]);
export type Term = typeof Term.Type;

export class PartialTriple extends S.Class<PartialTriple>("PartialTriple")({
  s: S.optionalKey(Term),
  p: S.optionalKey(Term),
  o: S.optionalKey(Term),
}, { description: "Partial triple pattern for query wildcards." }) {}

export class Triple extends S.Class<Triple>("Triple")({
  s: Term,
  p: Term,
  o: Term,
  g: S.optionalKey(S.String),
}, { description: "TrustGraph wire triple, optionally scoped to a named graph." }) {}
