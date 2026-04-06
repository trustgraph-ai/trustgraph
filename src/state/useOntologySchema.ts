import { useMemo } from "react";
import { useTriples } from "@trustgraph/react-state";
import { COLLECTION } from "../config";
const RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label";
const RDFS_DOMAIN = "http://www.w3.org/2000/01/rdf-schema#domain";
const RDFS_RANGE = "http://www.w3.org/2000/01/rdf-schema#range";
const RDFS_COMMENT = "http://www.w3.org/2000/01/rdf-schema#comment";
const OWL_CLASS = "http://www.w3.org/2002/07/owl#Class";
const OWL_OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#ObjectProperty";
const OWL_DATATYPE_PROPERTY = "http://www.w3.org/2002/07/owl#DatatypeProperty";

// Helper to extract value from a Term
function getTermValue(term: { t: string; i?: string; v?: string }): string {
  if (term.t === "i") return term.i || "";
  if (term.t === "l") return term.v || "";
  return "";
}

// Helper to get local name from URI
function getLocalName(uri: string): string {
  const hashIndex = uri.lastIndexOf("#");
  const slashIndex = uri.lastIndexOf("/");
  const index = Math.max(hashIndex, slashIndex);
  return index >= 0 ? uri.substring(index + 1) : uri;
}

export interface OntologyClass {
  uri: string;
  label: string;
  comment?: string;
}

export interface OntologyProperty {
  uri: string;
  label: string;
  domain?: string;
  range?: string;
}

export interface OntologySchema {
  classes: OntologyClass[];
  objectProperties: OntologyProperty[];
  datatypeProperties: OntologyProperty[];
  // Sets for quick lookup
  objectPropertyUris: Set<string>;
  datatypePropertyUris: Set<string>;
}

export function useOntologySchema() {
  // Query for classes
  const classTriples = useTriples({
    p: { t: "i", i: RDF_TYPE },
    o: { t: "i", i: OWL_CLASS },
    limit: 100,
    collection: COLLECTION,
  });

  // Query for object properties
  const objectPropertyTriples = useTriples({
    p: { t: "i", i: RDF_TYPE },
    o: { t: "i", i: OWL_OBJECT_PROPERTY },
    limit: 100,
    collection: COLLECTION,
  });

  // Query for datatype properties
  const datatypePropertyTriples = useTriples({
    p: { t: "i", i: RDF_TYPE },
    o: { t: "i", i: OWL_DATATYPE_PROPERTY },
    limit: 100,
    collection: COLLECTION,
  });

  // Query for all triples to get labels, domains, ranges
  const allTriples = useTriples({
    limit: 1000,
    collection: COLLECTION,
  });

  const isLoading = classTriples.isLoading || objectPropertyTriples.isLoading ||
                    datatypePropertyTriples.isLoading || allTriples.isLoading;
  const isError = classTriples.isError || objectPropertyTriples.isError ||
                  datatypePropertyTriples.isError || allTriples.isError;
  const error = classTriples.error || objectPropertyTriples.error ||
                datatypePropertyTriples.error || allTriples.error;

  const schema = useMemo((): OntologySchema | undefined => {
    if (isLoading) return undefined;

    // Build a map of URI -> metadata from all triples
    const metadata = new Map<string, { label?: string; domain?: string; range?: string; comment?: string }>();

    for (const triple of allTriples.triples || []) {
      const subject = getTermValue(triple.s);
      const predicate = getTermValue(triple.p);
      const value = getTermValue(triple.o);

      if (!metadata.has(subject)) {
        metadata.set(subject, {});
      }
      const meta = metadata.get(subject)!;

      if (predicate === RDFS_LABEL) {
        meta.label = value;
      } else if (predicate === RDFS_DOMAIN) {
        meta.domain = value;
      } else if (predicate === RDFS_RANGE) {
        meta.range = value;
      } else if (predicate === RDFS_COMMENT) {
        meta.comment = value;
      }
    }

    // Build classes list
    const classes: OntologyClass[] = [];
    for (const triple of classTriples.triples || []) {
      const uri = getTermValue(triple.s);
      const meta = metadata.get(uri) || {};
      classes.push({
        uri,
        label: meta.label || getLocalName(uri),
        comment: meta.comment,
      });
    }

    // Build object properties list
    const objectProperties: OntologyProperty[] = [];
    const objectPropertyUris = new Set<string>();
    for (const triple of objectPropertyTriples.triples || []) {
      const uri = getTermValue(triple.s);
      const meta = metadata.get(uri) || {};
      objectPropertyUris.add(uri);
      objectProperties.push({
        uri,
        label: meta.label || getLocalName(uri),
        domain: meta.domain,
        range: meta.range,
      });
    }

    // Build datatype properties list
    const datatypeProperties: OntologyProperty[] = [];
    const datatypePropertyUris = new Set<string>();
    for (const triple of datatypePropertyTriples.triples || []) {
      const uri = getTermValue(triple.s);
      const meta = metadata.get(uri) || {};
      datatypePropertyUris.add(uri);
      datatypeProperties.push({
        uri,
        label: meta.label || getLocalName(uri),
        domain: meta.domain,
        range: meta.range,
      });
    }

    return {
      classes,
      objectProperties,
      datatypeProperties,
      objectPropertyUris,
      datatypePropertyUris,
    };
  }, [
    isLoading,
    classTriples.triples,
    objectPropertyTriples.triples,
    datatypePropertyTriples.triples,
    allTriples.triples,
  ]);

  return {
    schema,
    isLoading,
    isError,
    error,
  };
}
