// Document RAG (Retrieval Augmented Generation) module
// Implements document-based RAG using chunk embeddings
// Provides semantic search and context-aware question answering
// Supports MCP (Model Context Protocol) tool integration

local helpers = import "helpers.jsonnet";
local flow = helpers.flow;
local request = helpers.request;
local response = helpers.response;
local request_response = helpers.request_response;
local llm_parameters = import "llm-parameters.jsonnet";

{
    // External interfaces for document RAG functionality
    "interfaces" +: {
        // Document embedding storage and retrieval
        "document-embeddings-store": flow("document-embeddings-store:{id}"), // Embedding storage stream
        "document-rag": request_response("document-rag:{id}"),            // Main document RAG interface
        "document-embeddings": request_response("document-embeddings:{id}"), // Document embedding queries

        // Supporting services
        "embeddings": request_response("embeddings:{id}"),           // General embedding service
        "prompt": request_response("prompt:{id}"),                   // Prompt processing
        "mcp-tool": request_response("mcp-tool:{id}"),               // MCP tool integration
        "text-completion": request_response("text-completion:{id}"),  // LLM text completion
    },

    // Parameters that can be configured for this flow
    "parameters" +: llm_parameters,

    // Flow-level processors for document embedding and storage
    "flow" +: {
        "document-embeddings:{id}": {
            input: flow("chunk-load:{id}"),
            output: flow("document-embeddings-store:{id}"),
            "embeddings-request": request("embeddings:{id}"),
            "embeddings-response": response("embeddings:{id}"),
        },
        "de-write:{id}": {
            input: flow("document-embeddings-store:{id}"),
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
        "document-rag:{id}": {
            request: request("document-rag:{id}"),
            response: response("document-rag:{id}"),
            "embeddings-request": request("embeddings:{id}"),
            "embeddings-response": response("embeddings:{id}"),
            "prompt-request": request("prompt-rag:{id}"),
            "prompt-response": response("prompt-rag:{id}"),
            "document-embeddings-request": request("document-embeddings:{id}"),
            "document-embeddings-response": response("document-embeddings:{id}"),
        },
        "de-query:{id}": {
            request: request("document-embeddings:{id}"),
            response: response("document-embeddings:{id}"),
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
        "mcp-tool:{id}": {
            request: request("mcp-tool:{id}"),
            response: response("mcp-tool:{id}"),
            "text-completion-request": request("text-completion:{id}"),
            "text-completion-response": response("text-completion:{id}"),
        },
        "metering:{id}": {
            input: response("text-completion:{id}"),
        },
        "metering-rag:{id}": {
            input: response("text-completion-rag:{id}"),
        },
    },

    // Blueprint-level processors for document RAG operations
    "blueprint" +: {
    }
}