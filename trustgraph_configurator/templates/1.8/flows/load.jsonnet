// Document loading and preprocessing module
// Handles document ingestion, format conversion, and chunking
// Converts PDFs to text and splits documents into processable chunks

local helpers = import "helpers.jsonnet";
local flow = helpers.flow;
local request = helpers.request;
local response = helpers.response;
local request_response = helpers.request_response;

{

    // External interfaces for document loading
    "interfaces" +: {
        "document-load": flow("document-load:{id}"),       // Raw document input stream
        "text-load": flow("text-document-load:{id}"),     // Text document stream
        "embeddings": request_response("embeddings:{id}"), // Embedding service for chunks
    },

    // No configurable parameters for document loading
    "parameters" +: {
    },

    // Flow-level processors for document preprocessing
    "flow" +: {
        // PDF decoder converts PDF documents to text
        "pdf-decoder:{id}": {
            input: flow("document-load:{id}"),         // Raw PDF input
            output: flow("text-document-load:{id}"),   // Extracted text output
        },

        // Chunker splits documents into smaller, processable pieces
        "chunker:{id}": {
            input: flow("text-document-load:{id}"),    // Full text documents
            output: flow("chunk-load:{id}"),            // Document chunks for processing
            "chunk-size": "{chunk-size}",              // Chunk size
            "chunk-overlap": "{chunk-overlap}",        // Overlap between chunks
        },
        // Embedding service for converting text chunks to vectors
        "embeddings:{id}": {
            request: request("embeddings:{id}"),   // Embedding requests
            response: response("embeddings:{id}"),  // Embedding responses
            model: "{embeddings-model}",
        },
    },

    // Blueprint-level processors for document loading services
    "blueprint" +: {
    }
}