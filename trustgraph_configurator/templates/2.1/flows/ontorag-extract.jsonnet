// OntologyRAG extraction module
// Extraction method for OntologyRAG - extracts using ontology definitions
// Mutually exclusive with GraphRAG extraction (both write to graph store)

local helpers = import "helpers.jsonnet";
local flow = helpers.flow;
local request = helpers.request;
local response = helpers.response;

{
    // No external interfaces - this module provides internal extraction services
    "interfaces" +: {
    },

    // No configurable parameters for basic KG extraction
    "parameters" +: {
    },

    // Flow-level processors for knowledge extraction
    "flow" +: {
        // Extracts using ontology definitions
        "kg-extract-ontology:{id}": {
            input: flow("chunk-load:{id}"),           // Input text chunks
            triples: flow("triples-store:{id}"),      // Output triples
            "entity-contexts": flow("entity-contexts-load:{id}"), // Entity context information
            "prompt-request": request("prompt:{id}"),   // Definition
                                                        // extraction prompts
            "prompt-response": response("prompt:{id}"),
            "embeddings-request": request("embeddings:{id}"),
            "embeddings-response": response("embeddings:{id}"),
        },

    },

    // No blueprint-level processors needed
    "blueprint" +: {
    }
}

