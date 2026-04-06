// Knowledge Graph Core storage module
// Handles persistent storage of knowledge graph data
// Consolidates triples and graph embeddings into permanent storage
// Creates the core knowledge base for long-term use

local helpers = import "helpers.jsonnet";
local flow = helpers.flow;

{
    // No external interfaces - internal storage service
    "interfaces" +: {
    },

    // No configurable parameters for core storage
    "parameters" +: {
    },

    // Flow-level processors for knowledge graph storage
    "flow" +: {
        // Knowledge graph store consolidates extracted knowledge
        // Takes processed triples and embeddings and stores them permanently
        "kg-store:{id}": {
            "triples-input": flow("triples-store:{id}"),           // Input RDF triples stream
            "graph-embeddings-input": flow("graph-embeddings-store:{id}"), // Input graph embeddings
        },
    },

    // No class-level processors needed
    "class" +: {
    }
}