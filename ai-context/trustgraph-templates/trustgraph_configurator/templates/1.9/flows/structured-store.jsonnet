// Structured store module
// Shared infrastructure for structured data RAG
// Handles object storage, retrieval, and NLP query capabilities

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
        // Object storage and querying
        "objects-store": flow("objects-store:{id}"),
        "objects": request_response("objects:{id}"),

        // Query interfaces
        "nlp-query": request_response("nlp-query:{id}"),
        "structured-query": request_response("structured-query:{id}"),
        "structured-diag": request_response("structured-diag:{id}"),
    },

    // Flow-level processors for structured storage and query
    "flow" +: {
        "objects-write:{id}": {
            input: flow("objects-store:{id}"),
        },
        "objects-query:{id}": {
            request: request("objects:{id}"),
            response: response("objects:{id}"),
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
            "objects-query-request": request("objects:{id}"),
            "objects-query-response": response("objects:{id}"),
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
