// Document loading and preprocessing module
// Handles document ingestion, format conversion, and chunking
// Converts PDFs to text and splits documents into processable chunks

local helpers = import "helpers.jsonnet";
local flow = helpers.flow;
local request = helpers.request;
local response = helpers.response;
local request_response = helpers.request_response;

// Import shared services (load requires embeddings for chunk processing)
local embeddings_service = import "embeddings-service.jsonnet";

// Merge shared services with load-specific configuration
embeddings_service + {

    // External interfaces for document loading
    "interfaces" +: {
        "document-load": flow("document-load:{id}"),
        "text-load": flow("text-document-load:{id}"),
    },

    // Flow-level processors for document preprocessing
    "flow" +: {
        // PDF decoder converts PDF documents to text
        "pdf-decoder:{id}": {
            input: flow("document-load:{id}"),
            output: flow("text-document-load:{id}"),
        },

        // Chunker splits documents into smaller, processable pieces
        "chunker:{id}": {
            input: flow("text-document-load:{id}"),
            output: flow("chunk-load:{id}"),
            "chunk-size": "{chunk-size}",
            "chunk-overlap": "{chunk-overlap}",
        },
    },

    // Blueprint-level processors for document loading services
    "blueprint" +: {
    },
}
