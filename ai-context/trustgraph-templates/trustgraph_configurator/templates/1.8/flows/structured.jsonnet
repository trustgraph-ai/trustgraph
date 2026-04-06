// Structured data processing module
// Handles extraction and querying of structured data objects
// Provides natural language to GraphQL query capabilities
// Supports structured data storage and retrieval

local helpers = import "helpers.jsonnet";
local flow = helpers.flow;
local request = helpers.request;
local response = helpers.response;
local request_response = helpers.request_response;
local llm_parameters = import "llm-parameters.jsonnet";

{
    // External interfaces for structured data operations
    "interfaces" +: {
        // Supporting services
        "embeddings": request_response("embeddings:{id}"),           // Embedding service
        "prompt": request_response("prompt:{id}"),                   // Prompt processing
        "text-completion": request_response("text-completion:{id}"),  // LLM completion

        // Structured data storage and querying
        "objects-store": flow("objects-store:{id}"),                    // Object storage stream
        "objects": request_response("objects:{id}"),                 // Object query service

        // Query interfaces
        "nlp-query": request_response("nlp-query:{id}"),             // NLP to GraphQL translation
        "structured-query": request_response("structured-query:{id}"), // Structured query execution
        "structured-diag": request_response("structured-diag:{id}"),  // Query diagnostics
    },


    // Parameters that can be configured for this flow
    "parameters" +: llm_parameters,

    // Flow-level processors for structured data extraction
    "flow" +: {
        "kg-extract-objects:{id}": {
            input: flow("chunk-load:{id}"),
            output: flow("objects-store:{id}"),
            "entity-contexts": flow("entity-contexts-load:{id}"),
            "prompt-request": request("prompt:{id}"),
            "prompt-response": response("prompt:{id}"),
        },
        "objects-write:{id}": {
            input: flow("objects-store:{id}"),
        },
        "text-completion:{id}": {
            request: request("text-completion:{id}"),
            response: response("text-completion:{id}"),
            model: "{llm-model}",
        },
        "text-completion-rag:{id}": {
            request: request("text-completion-rag:{id}"),
            response: response("text-completion-rag:{id}"),
            model: "{llm-rag-model}",
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
        "embeddings:{id}": {
            request: request("embeddings:{id}"),
            response: response("embeddings:{id}"),
            model: "{embeddings-model}",
        },
        "prompt:{id}": {
            request: request("prompt:{id}"),
            response: response("prompt:{id}"),
            "text-completion-request": request("text-completion:{id}"),
            "text-completion-response": response("text-completion:{id}"),
        },
        "prompt-rag:{id}": {
            request: request("prompt-rag:{id}"),
            response: response("prompt-rag:{id}"),
            "text-completion-request": request("text-completion-rag:{id}"),
            "text-completion-response": response("text-completion-rag:{id}"),
        },
        "metering:{id}": {
            input: response("text-completion:{id}"),
        },
        "metering-rag:{id}": {
            input: response("text-completion-rag:{id}"),
        },
    },
    // Blueprint-level processors for structured data operations
    "blueprint" +: {
    }
}