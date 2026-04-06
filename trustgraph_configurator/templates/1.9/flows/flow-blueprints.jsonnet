// TrustGraph Flow Blueprints Configuration
//
// RAG Modes (4 types):
// - Document RAG: Uses document chunk embeddings
// - Graph RAG: Extracts definitions + relationships to graph
// - Ontology RAG: Extracts using ontology definitions to graph (mutually exclusive with Graph RAG)
// - Structured RAG: Extracts objects to object store
//
// Module structure:
// - *-store: Storage and query infrastructure
// - *-extract: Extraction methods

// Import all the modular flow components
local graph_store = import "graph-store.jsonnet";
local document_store = import "document-store.jsonnet";
local structured_store = import "structured-store.jsonnet";
local graphrag_extract = import "graphrag-extract.jsonnet";
local ontorag_extract = import "ontorag-extract.jsonnet";
local structured_extract = import "structured-extract.jsonnet";
local agent = import "agent.jsonnet";
local load = import "load.jsonnet";
local kgcore = import "kgcore.jsonnet";

{

    // Full system: Graph RAG + Document RAG + knowledge cores
    "everything": {
        description: "Graph RAG + Document RAG + knowledge cores",
        tags: ["document-rag", "graph-rag", "kgcore"],
    } +
      graph_store + document_store + agent + load +
      graphrag_extract + kgcore,

    // Structured RAG only
    "structured": {
        description: "Structured data extraction and querying",
        tags: ["structured"],
    } +
      structured_store + structured_extract + agent + load,

    // Ontology RAG + knowledge cores
    "ontology": {
        description: "Ontology RAG + knowledge cores",
        tags: ["onto-rag", "kgcore"],
    } +
      graph_store + ontorag_extract + agent + load + kgcore,

}
