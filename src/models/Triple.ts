// Term type discriminators matching the wire format
// i = IRI, b = BLANK node, l = LITERAL, t = TRIPLE (reified)
export type TermType = "i" | "b" | "l" | "t";

export interface IriTerm {
  t: "i";
  i: string;
}

export interface BlankTerm {
  t: "b";
  d: string;
}

export interface LiteralTerm {
  t: "l";
  v: string;
  dt?: string;  // datatype
  ln?: string;  // language
}

export interface TripleTerm {
  t: "t";
  tr?: Triple;
}

export type Term = IriTerm | BlankTerm | LiteralTerm | TripleTerm;

export interface PartialTriple {
  s?: Term;
  p?: Term;
  o?: Term;
}

export interface Triple {
  s: Term;
  p: Term;
  o: Term;
  g?: string;  // graph (renamed from direc to match backend)
}
