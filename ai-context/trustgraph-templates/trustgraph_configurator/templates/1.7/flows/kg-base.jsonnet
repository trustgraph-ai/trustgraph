// Knowledge Graph Base extraction module
// Provides basic knowledge extraction capabilities from text chunks
// Extracts entity definitions and relationships using prompt-based processing

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
        // Extracts entity definitions from text chunks
        // Identifies and defines key entities mentioned in the text
        "kg-extract-definitions:{id}": {
            input: flow("chunk-load:{id}"),                       // Input text chunks
            triples: flow("triples-store:{id}"),                  // Output definition triples
            "entity-contexts": flow("entity-contexts-load:{id}"), // Entity context information
            "prompt-request": request("prompt:{id}"),          // Definition extraction prompts
            "prompt-response": response("prompt:{id}"),
        },

        // Extracts relationships between entities
        // Identifies how entities are connected and interact
        "kg-extract-relationships:{id}": {
            input: flow("chunk-load:{id}"),                // Input text chunks
            triples: flow("triples-store:{id}"),           // Output relationship triples
            "prompt-request": request("prompt:{id}"),   // Relationship extraction prompts
            "prompt-response": response("prompt:{id}"),
        },
    },

    // No class-level processors needed
    "class" +: {
    }
}