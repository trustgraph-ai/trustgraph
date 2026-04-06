// Graph store module
// Shared infrastructure for graph-based RAG (used by both GraphRAG and OntologyRAG)
// Handles knowledge graph storage, embeddings, and graph-based question answering

local helpers = import "helpers.jsonnet";
local flow = helpers.flow;
local request = helpers.request;
local response = helpers.response;
local request_response = helpers.request_response;

// Import shared services
local llm_services = import "llm-services.jsonnet";
local embeddings_service = import "embeddings-service.jsonnet";

// Merge shared services with graph store configuration
llm_services + embeddings_service + {

    // External interfaces exposed by the graph store
    "interfaces" +: {
        // Data ingestion interfaces for graph construction
        "entity-contexts-load": flow("entity-contexts-load:{id}"),
        "triples-store": flow("triples-store:{id}"),
        "graph-embeddings-store": flow("graph-embeddings-store:{id}"),

        // Query interfaces for graph-based operations
        "graph-rag": request_response("graph-rag:{id}"),
        "triples": request_response("triples:{id}"),
        "graph-embeddings": request_response("graph-embeddings:{id}"),
    },

    // Flow-level processors - handle data streams for a specific flow instance
    "flow" +: {
        "graph-embeddings:{id}": {
            input: flow("entity-contexts-load:{id}"),
            output: flow("graph-embeddings-store:{id}"),
            "embeddings-request": request("embeddings:{id}"),
            "embeddings-response": response("embeddings:{id}"),
        },
        "triples-write:{id}": {
            input: flow("triples-store:{id}"),
        },
        "ge-write:{id}": {
            input: flow("graph-embeddings-store:{id}"),
        },
        "graph-rag:{id}": {
            request: request("graph-rag:{id}"),
            response: response("graph-rag:{id}"),
            "embeddings-request": request("embeddings:{id}"),
            "embeddings-response": response("embeddings:{id}"),
            "prompt-request": request("prompt-rag:{id}"),
            "prompt-response": response("prompt-rag:{id}"),
            "graph-embeddings-request": request("graph-embeddings:{id}"),
            "graph-embeddings-response": response("graph-embeddings:{id}"),
            "triples-request": request("triples:{id}"),
            "triples-response": response("triples:{id}"),
        },
        "triples-query:{id}": {
            request: request("triples:{id}"),
            response: response("triples:{id}"),
        },
        "ge-query:{id}": {
            request: request("graph-embeddings:{id}"),
            response: response("graph-embeddings:{id}"),
        },
    },

    // Blueprint-level processors - shared across all flow instances of this blueprint
    "blueprint" +: {
    },
}
