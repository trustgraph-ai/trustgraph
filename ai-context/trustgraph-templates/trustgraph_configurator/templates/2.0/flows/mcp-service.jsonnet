// Shared MCP (Model Context Protocol) tool service module
// Provides MCP tool execution capabilities for agents
// Import this module in any flow that requires MCP tool integration

local helpers = import "helpers.jsonnet";
local request = helpers.request;
local response = helpers.response;
local request_response = helpers.request_response;

{
    // Interfaces exposed by MCP service
    "interfaces" +: {
        "mcp-tool": request_response("mcp-tool:{id}"),
    },

    "parameters" +: {
    },

    // Flow-level processor for MCP tool execution
    "flow" +: {
        "mcp-tool:{id}": {
            request: request("mcp-tool:{id}"),
            response: response("mcp-tool:{id}"),
            "text-completion-request": request("text-completion:{id}"),
            "text-completion-response": response("text-completion:{id}"),
        },
    },

    "blueprint" +: {
    },
}
