// TrustGraph Flow Classes Configuration
// Defines different flow combinations for various use cases
// Each flow class combines multiple functional modules to create complete processing pipelines
//
// Available modules:
// - graphrag: Graph-based RAG with knowledge graphs
// - documentrag: Document-based RAG with chunk embeddings
// - structured: Structured data processing and NLP queries
// - agent: AI agent orchestration and tool integration
// - load: Document loading and preprocessing
// - kg-base: Basic knowledge extraction from text
// - agent-extract: Agent-based knowledge extraction
// - kgcore: Knowledge graph core storage

// Import all the modular flow components
local graphrag_part = import "graphrag.jsonnet";
local kg_base_part = import "kg-base.jsonnet";
local onto_base_part = import "onto-base.jsonnet";
local agent_extract_part = import "agent-extract.jsonnet";
local structured_part = import "structured.jsonnet";
local documentrag_part = import "documentrag.jsonnet";
local agent_part = import "agent.jsonnet";
local load_part = import "load.jsonnet";
local kgcore_part = import "kgcore.jsonnet";

{

    // Complete TrustGraph system with all capabilities
    // Includes GraphRAG, DocumentRAG, structured data processing, and knowledge cores
    "everything": {
        description: "GraphRAG, DocumentRAG, structured data + knowledge cores",
        tags: [
            "document-rag", "graph-rag", "knowledge-extraction",
            "structured-data", "kgcore"
        ],
    } +
      graphrag_part + documentrag_part + agent_part + load_part +
      kg_base_part + structured_part,

    // Dual RAG system without knowledge core creation
    // Combines both document and graph-based retrieval
    "document-rag+graph-rag": {
        description: "Supports GraphRAG and document RAG, no core creation",
        tags: ["document-rag", "graph-rag", "knowledge-extraction"],
    } +
      graphrag_part + documentrag_part + agent_part + load_part + kg_base_part,

    // Graph-based RAG only
    // Uses knowledge graphs for context-aware question answering
    "graph-rag": {
        description: "GraphRAG only",
        tags: ["graph-rag", "knowledge-extraction"],
    } +
      graphrag_part + agent_part + load_part + kg_base_part,

    // Graph-based RAG only
    // Uses knowledge graphs for context-aware question answering
    "onto-rag": {
        description: "Ontology RAG only",
        tags: ["graph-rag", "knowledge-extraction"],
    } +
      graphrag_part + agent_part + load_part + onto_base_part,

    // Document-based RAG only
    // Uses document embeddings for semantic search and answers
    "document-rag": {
        description: "DocumentRAG only",
        tags: ["document-rag"],
    } +
      documentrag_part + load_part,

    // Full RAG system with knowledge core creation
    // Includes both RAG types plus persistent knowledge storage
    "document-rag+graph-rag+kgcore": {
        description: "GraphRAG + DocumentRAG + knowledge core creation",
        tags: ["document-rag", "graph-rag", "knowledge-extraction"],
    } +
      graphrag_part + documentrag_part + agent_part + load_part +
      kgcore_part + kg_base_part,

    // GraphRAG with advanced agent-based extraction
    // Uses AI agents for sophisticated knowledge extraction
    "graph-rag+agent-extract": {
        description: "GraphRAG + agent extract",
        tags: ["graph-rag", "knowledge-extraction", "agent-extract"],
    } +
      graphrag_part + agent_part + load_part + agent_extract_part,

    // GraphRAG with structured data processing
    // Combines knowledge graphs with structured data queries
    "graph-rag+structured-data": {
        description: "GraphRAG + structured data",
        tags: ["graph-rag", "knowledge-extraction", "structured-data"],
    } +
      graphrag_part + agent_part + load_part + structured_part,

    // Structured data processing only
    // Handles structured data extraction and NLP queries
    "structured-data": {
        description: "Structured data only",
        tags: ["knowledge-extraction", "structured-data"],
    } +
      agent_part + load_part + structured_part,

}