// Agent-based extraction module
// Uses AI agents for more sophisticated knowledge extraction from text
// Leverages agent tools and reasoning for complex extraction tasks

local helpers = import "helpers.jsonnet";
local flow = helpers.flow;
local request = helpers.request;
local response = helpers.response;

{
    // No external interfaces - internal agent extraction service
    "interfaces" +: {
    },

    // No configurable parameters for agent extraction
    "parameters" +: {
    },

    // Flow-level processors for agent-based extraction
    "flow" +: {
        // Agent-based knowledge extraction processor
        // Uses AI agents with tools to extract structured knowledge
        "kg-extract-agent:{id}": {
            input: flow("chunk-load:{id}"),                       // Input text chunks
            triples: flow("triples-store:{id}"),                  // Output knowledge triples
            "entity-contexts": flow("entity-contexts-load:{id}"), // Entity context information
            "agent-request": request("agent:{id}"),               // Agent service requests
            "agent-response": response("agent:{id}"),             // Agent service responses
        },
    },

    // No class-level processors needed
    "class" +: {
    }
}