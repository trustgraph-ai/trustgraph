// Structured store module
// Shared infrastructure for structured data RAG
// Handles row storage, retrieval, and NLP query capabilities

local helpers = import "helpers.jsonnet";
local flow = helpers.flow;
local request = helpers.request;
local response = helpers.response;
local request_response = helpers.request_response;

// Import shared services
local llm_services = import "llm-services.jsonnet";
local embeddings_service = import "embeddings-service.jsonnet";

// Merge shared services with structured store configuration
llm_services + embeddings_service + {

    // External interfaces for structured store
    "interfaces" +: {
        // Row storage and querying
        "rows-store": flow("rows-store:{id}"),
        "row-embeddings-store": flow("row-embeddings-store:{id}"),
        "rows": request_response("rows:{id}"),
        "row-embeddings": request_response("row-embeddings:{id}"),

        // Query interfaces
        "nlp-query": request_response("nlp-query:{id}"),
        "structured-query": request_response("structured-query:{id}"),
        "structured-diag": request_response("structured-diag:{id}"),
    },

    // Flow-level processors for structured storage and query
    "flow" +: {
        "row-embeddings:{id}": {
            input: flow("rows-store:{id}"),
            output: flow("row-embeddings-store:{id}"),
            "embeddings-request": request("embeddings:{id}"),
            "embeddings-response": response("embeddings:{id}"),
        },
        "rows-write:{id}": {
            input: flow("rows-store:{id}"),
        },
        "row-embeddings-write:{id}": {
            input: flow("row-embeddings-store:{id}"),
        },
        "rows-query:{id}": {
            request: request("rows:{id}"),
            response: response("rows:{id}"),
        },
        "row-embeddings-query:{id}": {
            request: request("row-embeddings:{id}"),
            response: response("row-embeddings:{id}"),
        },
        "nlp-query:{id}": {
            request: request("nlp-query:{id}"),
            response: response("nlp-query:{id}"),
            "prompt-request": request("prompt-rag:{id}"),
            "prompt-response": response("prompt-rag:{id}"),
        },
        "structured-query:{id}": {
            request: request("structured-query:{id}"),
            response: response("structured-query:{id}"),
            "nlp-query-request": request("nlp-query:{id}"),
            "nlp-query-response": response("nlp-query:{id}"),
            "rows-query-request": request("rows:{id}"),
            "rows-query-response": response("rows:{id}"),
        },
        "structured-diag:{id}": {
            request: request("structured-diag:{id}"),
            response: response("structured-diag:{id}"),
            "prompt-request": request("prompt:{id}"),
            "prompt-response": response("prompt:{id}"),
        },
    },

    "blueprint" +: {
    },
}
