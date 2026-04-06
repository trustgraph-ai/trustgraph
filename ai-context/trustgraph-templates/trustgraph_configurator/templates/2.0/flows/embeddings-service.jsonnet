// Shared embeddings service module
// Provides vector embedding generation for text
// Import this module in any flow that requires embeddings

local helpers = import "helpers.jsonnet";
local request = helpers.request;
local response = helpers.response;
local request_response = helpers.request_response;

{
    // Interfaces exposed by embeddings service
    "interfaces" +: {
        "embeddings": request_response("embeddings:{id}"),
    },

    "parameters" +: {
    },

    // Flow-level processor for embeddings
    "flow" +: {
        "embeddings:{id}": {
            request: request("embeddings:{id}"),
            response: response("embeddings:{id}"),
            model: "{embeddings-model}",
        },
    },

    "blueprint" +: {
    },
}
