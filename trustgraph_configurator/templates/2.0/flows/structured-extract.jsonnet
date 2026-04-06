// Structured RAG extraction module
// Extracts structured rows from text chunks
// Outputs to rows-store for structured data querying

local helpers = import "helpers.jsonnet";
local flow = helpers.flow;
local request = helpers.request;
local response = helpers.response;

{
    "interfaces" +: {
    },

    "parameters" +: {
    },

    // Flow-level processor for structured row extraction
    "flow" +: {
        "kg-extract-rows:{id}": {
            input: flow("chunk-load:{id}"),
            output: flow("rows-store:{id}"),
            "entity-contexts": flow("entity-contexts-load:{id}"),
            "prompt-request": request("prompt:{id}"),
            "prompt-response": response("prompt:{id}"),
        },
    },

    "blueprint" +: {
    },
}
