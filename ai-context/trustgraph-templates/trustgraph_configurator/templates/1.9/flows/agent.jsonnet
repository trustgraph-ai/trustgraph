// Agent management module
// Provides AI agent orchestration and tool integration
// Manages agent conversations, tool calls, and response coordination
// Supports MCP tools, GraphRAG, and structured queries

local helpers = import "helpers.jsonnet";
local request = helpers.request;
local response = helpers.response;
local request_response = helpers.request_response;

// Import shared services (agent requires LLM for reasoning, MCP for tools)
local llm_services = import "llm-services.jsonnet";
local mcp_service = import "mcp-service.jsonnet";

// Merge shared services with agent-specific configuration
llm_services + mcp_service + {

    // External interfaces for agent operations
    "interfaces" +: {
        "agent": request_response("agent:{id}"),
    },

    // Flow-level processors for agent management
    "flow" +: {
        // Agent manager orchestrates agent conversations and tool usage
        "agent-manager:{id}": {
            // Agent communication channels
            request: request("agent:{id}"),
            next: request("agent:{id}"),
            response: response("agent:{id}"),

            // LLM and prompt services
            "text-completion-request": request("text-completion:{id}"),
            "text-completion-response": response("text-completion:{id}"),
            "prompt-request": request("prompt:{id}"),
            "prompt-response": response("prompt:{id}"),

            // Tool integrations
            "mcp-tool-request": request("mcp-tool:{id}"),
            "mcp-tool-response": response("mcp-tool:{id}"),
            "graph-rag-request": request("graph-rag:{id}"),
            "graph-rag-response": response("graph-rag:{id}"),
            "structured-query-request": request("structured-query:{id}"),
            "structured-query-response": response("structured-query:{id}"),
        },
    },

    // Blueprint-level processors for agent-related services
    "blueprint" +: {
    },
}
