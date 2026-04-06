/**
 * RDF namespace constants for TrustGraph
 * Used for querying explainability data, provenance chains, and knowledge graph
 */

// TrustGraph namespace
export const TG = "https://trustgraph.ai/ns/";
export const TG_QUERY = TG + "query";
export const TG_EDGE_COUNT = TG + "edgeCount";
export const TG_SELECTED_EDGE = TG + "selectedEdge";
export const TG_EDGE = TG + "edge";
export const TG_REASONING = TG + "reasoning";
export const TG_CONTENT = TG + "content";
export const TG_REIFIES = TG + "reifies";
export const TG_DOCUMENT = TG + "document";

// W3C PROV-O namespace
export const PROV = "http://www.w3.org/ns/prov#";
export const PROV_STARTED_AT_TIME = PROV + "startedAtTime";
export const PROV_WAS_DERIVED_FROM = PROV + "wasDerivedFrom";
export const PROV_WAS_GENERATED_BY = PROV + "wasGeneratedBy";
export const PROV_ACTIVITY = PROV + "Activity";
export const PROV_ENTITY = PROV + "Entity";

// RDFS namespace
export const RDFS = "http://www.w3.org/2000/01/rdf-schema#";
export const RDFS_LABEL = RDFS + "label";

// RDF namespace
export const RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#";
export const RDF_TYPE = RDF + "type";

// Schema.org namespace (used in document metadata)
export const SCHEMA = "https://schema.org/";
export const SCHEMA_NAME = SCHEMA + "name";
export const SCHEMA_DESCRIPTION = SCHEMA + "description";
export const SCHEMA_AUTHOR = SCHEMA + "author";
export const SCHEMA_KEYWORDS = SCHEMA + "keywords";

// SKOS namespace
export const SKOS = "http://www.w3.org/2004/02/skos/core#";
export const SKOS_DEFINITION = SKOS + "definition";
