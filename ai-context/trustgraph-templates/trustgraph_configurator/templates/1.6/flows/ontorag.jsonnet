// GraphRAG flow configuration module
// Implements graph-based retrieval augmented generation (GraphRAG) functionality
// Handles knowledge graph storage, embeddings, and graph-based question answering

local helpers = import "helpers.jsonnet";
local flow = helpers.flow;
local request = helpers.request;
local response = helpers.response;
local request_response = helpers.request_response;
local llm_parameters = import "llm-parameters.jsonnet";

{
    // External interfaces exposed by the GraphRAG flow
    "interfaces" +: {
        // Data ingestion interfaces for graph construction
        "entity-contexts-load": flow("entity-contexts-load:{id}"),      // Entity context data stream
        "triples-store": flow("triples-store:{id}"),                    // RDF triples storage stream
        "graph-embeddings-store": flow("graph-embeddings-store:{id}"),  // Graph embedding storage

        // Query interfaces for graph-based operations
        "graph-rag": request_response("graph-rag:{id}"),             // Main GraphRAG query interface
        "triples": request_response("triples:{id}"),                 // Triple store queries
        "graph-embeddings": request_response("graph-embeddings:{id}"), // Graph embedding queries

        // Supporting services
        "embeddings": request_response("embeddings:{id}"),           // General embedding service
        "prompt": request_response("prompt:{id}"),                   // Prompt processing service
        "text-completion": request_response("text-completion:{id}"),  // LLM text completion
    },


    // Parameters that can be configured for this flow
    "parameters" +: llm_parameters,

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
        "embeddings:{id}": {
            request: request("embeddings:{id}"),
            response: response("embeddings:{id}"),
            model: "{embeddings-model}",
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

    // Class-level processors - shared across all flow instances of this class
    "class" +: {
    }
}