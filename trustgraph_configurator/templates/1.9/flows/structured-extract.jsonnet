// Structured RAG extraction module
// Extracts structured objects from text chunks
// Outputs to objects-store for structured data querying

local helpers = import "helpers.jsonnet";
local flow = helpers.flow;
local request = helpers.request;
local response = helpers.response;

{
    "interfaces" +: {
    },

    "parameters" +: {
    },

    // Flow-level processor for structured object extraction
    "flow" +: {
        "kg-extract-objects:{id}": {
            input: flow("chunk-load:{id}"),
            output: flow("objects-store:{id}"),
            "entity-contexts": flow("entity-contexts-load:{id}"),
            "prompt-request": request("prompt:{id}"),
            "prompt-response": response("prompt:{id}"),
        },
    },

    "blueprint" +: {
    },
}
