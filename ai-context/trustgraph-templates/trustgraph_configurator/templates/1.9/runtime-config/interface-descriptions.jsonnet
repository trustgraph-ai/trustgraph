// Interface Descriptions Module
// Defines all external interfaces available in TrustGraph flows
// These are the 'endpoints' that external systems can interact with

{
    // Document loading interfaces - for data ingestion
    "document-load": {
        "description": "Document loader",
        "kind": "send",
        "visible": true,
    },
    "text-load": {
        "description": "Text document loader",
        "kind": "send",
        "visible": true,
    },

    // Data storage interfaces - for processed data streams
    "entity-contexts-load": {
        "description": "Entity contexts loader",
        "kind": "send",
    },
    "triples-store": {
        "description": "Triples loader",
        "kind": "send",
    },
    "graph-embeddings-store": {
        "description": "Graph embeddings loader",
        "kind": "send",
    },
    "document-embeddings-store": {
        "description": "Document embeddings loader",
        "kind": "send",
    },
    "objects-store": {
        "description": "Object store",
        "kind": "request-response",
    },

    // Query interfaces - for retrieving information
    "graph-rag": {
        "description": "GraphRAG service",
        "kind": "request-response",
    },
    "document-rag": {
        "description": "ChunkRAG service",
        "kind": "request-response",
    },
    "triples": {
        "description": "Triples query service",
        "kind": "request-response",
    },
    "graph-embeddings": {
        "description": "Graph embeddings service",
        "kind": "request-response",
    },
    "document-embeddings": {
        "description": "Document embeddings service",
        "kind": "request-response",
    },
    "objects": {
        "description": "Object query service",
        "kind": "request-response",
    },

    // Processing services - for text and data processing
    "prompt": {
        "description": "Prompt service",
        "kind": "request-response",
    },
    "agent": {
        "description": "Agent service",
        "kind": "request-response",
    },
    "text-completion": {
        "description": "Text completion service",
        "kind": "request-response",
    },

    // Query translation services - for natural language queries
    "nlp-query": {
        "description": "NLP question to GraphQL service",
        "kind": "request-response",
    },
    "structured-query": {
        "description": "Structured query service",
        "kind": "request-response",
    },
}