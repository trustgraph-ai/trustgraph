import { useState, useEffect, useMemo } from "react";
import { useSocket } from "@trustgraph/react-provider";
import type { Triple } from "@trustgraph/react-state";
import type { Entity, Relationship, DomainKey, OntologyType } from "../types";
import { COLLECTION } from "../config";
import { domainColors } from "../theme";

const RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label";
const RDFS_COMMENT = "http://www.w3.org/2000/01/rdf-schema#comment";
const OWL_CLASS = "http://www.w3.org/2002/07/owl#Class";
const OWL_DATATYPE_PROPERTY = "http://www.w3.org/2002/07/owl#DatatypeProperty";
const OWL_OBJECT_PROPERTY = "http://www.w3.org/2002/07/owl#ObjectProperty";

// Helper to extract value from a Term
function getTermValue(term: { t: string; i?: string; v?: string }): string {
  if (term.t === "i") return term.i || "";
  if (term.t === "l") return term.v || "";
  return "";
}

// Helper to create a short ID from a URI
function uriToId(uri: string): string {
  const hashIndex = uri.lastIndexOf("#");
  const slashIndex = uri.lastIndexOf("/");
  const index = Math.max(hashIndex, slashIndex);
  return index >= 0 ? uri.substring(index + 1) : uri;
}

// Helper to get icon for a class (placeholder for now)
function getClassIcon(_classUri: string): string {
  return "●";
}

// Helper to extract predicate name from URI
function predicateToName(uri: string): string {
  const hashIndex = uri.lastIndexOf("#");
  const slashIndex = uri.lastIndexOf("/");
  const index = Math.max(hashIndex, slashIndex);
  const name = index >= 0 ? uri.substring(index + 1) : uri;
  return name.replace(/([a-z])([A-Z])/g, "$1_$2").toLowerCase();
}

export function useGraphData(domain?: DomainKey) {
  const socket = useSocket();
  const [triples, setTriples] = useState<Triple[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        setIsLoading(true);
        setIsError(false);
        setError(null);

        const api = socket.flow("default");
        const result = await api.triplesQuery(
          undefined, undefined, undefined,
          10000, COLLECTION, "",
        );

        if (!cancelled) {
          setTriples(result);
          setIsLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setIsError(true);
          setError(err instanceof Error ? err : new Error(String(err)));
          setIsLoading(false);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [socket]);

  // Process all data from the query
  const { entities, relationships, ontology, propertyLabels } = useMemo(() => {
    if (isLoading || !triples) {
      return { entities: [], relationships: [], ontology: undefined, propertyLabels: {} };
    }

    // First pass: collect all labels, comments, and find OWL classes and properties
    const allLabels = new Map<string, string>();
    const allComments = new Map<string, string>();
    const owlClasses = new Set<string>();
    const propertyUris = new Set<string>();

    for (const triple of triples) {
      const subjectUri = getTermValue(triple.s);
      const predicate = getTermValue(triple.p);
      const objectUri = getTermValue(triple.o);

      if (predicate === RDFS_LABEL) {
        allLabels.set(subjectUri, getTermValue(triple.o));
      } else if (predicate === RDFS_COMMENT) {
        allComments.set(subjectUri, getTermValue(triple.o));
      } else if (predicate === RDF_TYPE) {
        if (objectUri === OWL_CLASS) {
          owlClasses.add(subjectUri);
        } else if (objectUri === OWL_DATATYPE_PROPERTY || objectUri === OWL_OBJECT_PROPERTY) {
          propertyUris.add(subjectUri);
        }
      }
    }

    // Build property labels map: local name -> label
    const propertyLabels: Record<string, string> = {};
    for (const propUri of propertyUris) {
      const localName = uriToId(propUri);
      const label = allLabels.get(propUri);
      if (label) {
        propertyLabels[localName] = label;
      }
    }

    // Build class config dynamically from discovered OWL classes
    const classConfig = new Map<string, { domain: DomainKey; color: string; glow: string; icon: string; label: string; description: string }>();
    let colorIndex = 0;
    for (const classUri of owlClasses) {
      const localName = uriToId(classUri).toLowerCase();
      const palette = domainColors[colorIndex % domainColors.length];
      classConfig.set(classUri, {
        domain: localName,
        color: palette.color,
        glow: palette.glow,
        icon: getClassIcon(classUri),
        label: allLabels.get(classUri) || uriToId(classUri),
        description: allComments.get(classUri) || "",
      });
      colorIndex++;
    }

    // Second pass: find entities (instances of OWL classes) and their properties
    const entityMap = new Map<string, Entity>();
    const entityProps = new Map<string, Record<string, string | number>>();

    // Collect entity properties first
    for (const triple of triples) {
      const subjectUri = getTermValue(triple.s);
      const predicate = getTermValue(triple.p);
      const value = getTermValue(triple.o);

      // Skip schema-level predicates and URIs as values
      if (predicate !== RDF_TYPE && predicate !== RDFS_LABEL && predicate !== RDFS_COMMENT &&
          value && !value.startsWith("http")) {
        if (!entityProps.has(subjectUri)) {
          entityProps.set(subjectUri, {});
        }
        const propName = uriToId(predicate);
        entityProps.get(subjectUri)![propName] = value;
      }
    }

    // Find entities by type (instances of OWL classes)
    for (const triple of triples) {
      const subjectUri = getTermValue(triple.s);
      const predicate = getTermValue(triple.p);
      const objectUri = getTermValue(triple.o);

      if (predicate === RDF_TYPE && classConfig.has(objectUri)) {
        const config = classConfig.get(objectUri)!;
        if (domain && config.domain !== domain) continue;

        const entityId = uriToId(subjectUri);
        entityMap.set(subjectUri, {
          id: entityId,
          uri: subjectUri,
          label: allLabels.get(subjectUri) || entityId,
          props: entityProps.get(subjectUri) || {},
          domain: config.domain,
          color: config.color,
          glow: config.glow,
          icon: config.icon,
        });
      }
    }

    // Find relationships: triples where both subject and object are known entities
    const relationships: Relationship[] = [];
    const entityUris = new Set(entityMap.keys());

    for (const triple of triples) {
      const subjectUri = getTermValue(triple.s);
      const predicate = getTermValue(triple.p);
      const objectUri = getTermValue(triple.o);

      // Skip rdf:type and rdfs:label
      if (predicate === RDF_TYPE || predicate === RDFS_LABEL) continue;

      // If both subject and object are entities, it's a relationship
      if (entityUris.has(subjectUri) && entityUris.has(objectUri)) {
        const fromEntity = entityMap.get(subjectUri)!;
        const toEntity = entityMap.get(objectUri)!;

        relationships.push({
          from: fromEntity.id,
          to: toEntity.id,
          predicate: predicateToName(predicate),
          domain: [fromEntity.domain, toEntity.domain],
        });
      }
    }

    const entities = Array.from(entityMap.values());

    // Build ontology metadata dynamically from discovered classes
    const ontology: OntologyType = {};
    for (const [, config] of classConfig) {
      ontology[config.domain] = {
        label: config.label,
        color: config.color,
        glow: config.glow,
        icon: config.icon,
        description: config.description,
        properties: [],
        subclasses: entities.filter(e => e.domain === config.domain).map(e => ({
          id: e.id,
          uri: e.uri,
          label: e.label,
          props: e.props,
        })),
      };
    }

    return { entities, relationships, ontology, propertyLabels };
  }, [isLoading, triples, domain]);

  return {
    entities,
    relationships,
    ontology,
    propertyLabels,
    isLoading,
    isError,
    error,
  };
}
