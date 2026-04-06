// Agent management module
// Provides AI agent orchestration and tool integration
// Manages agent conversations, tool calls, and response coordination
// Supports MCP tools, GraphRAG, and structured queries

local helpers = import "helpers.jsonnet";
local request = helpers.request;
local response = helpers.response;
local request_response = helpers.request_response;

{
    // External interfaces for agent operations
    "interfaces" +: {
        "agent": request_response("agent:{id}"),         // Main agent service interface
        "mcp-tool": request_response("mcp-tool:{id}"), // MCP tool execution interface
    },

    // No configurable parameters for agent management
    "parameters" +: {
    },

    // Flow-level processors for agent management
    "flow" +: {
        // Agent manager orchestrates agent conversations and tool usage
        "agent-manager:{id}": {
            // Agent communication channels
            request: request("agent:{id}"),                    // Incoming agent requests
            next: request("agent:{id}"),                      // Multi-turn conversation support
            response: response("agent:{id}"),                  // Agent responses

            // LLM and prompt services
            "text-completion-request": request("text-completion:{id}"),   // LLM requests
            "text-completion-response": response("text-completion:{id}"), // LLM responses
            "prompt-request": request("prompt:{id}"),                     // Prompt processing
            "prompt-response": response("prompt:{id}"),

            // Tool integrations
            "mcp-tool-request": request("mcp-tool:{id}"),                 // MCP tool calls
            "mcp-tool-response": response("mcp-tool:{id}"),
            "graph-rag-request": request("graph-rag:{id}"),               // GraphRAG queries
            "graph-rag-response": response("graph-rag:{id}"),
            "structured-query-request": request("structured-query:{id}"), // Structured data queries
            "structured-query-response": response("structured-query:{id}"),
        },

        // MCP tool executor for agent tool usage
        "mcp-tool:{id}": {
            request: request("mcp-tool:{id}"),                            // Tool invocation requests
            response: response("mcp-tool:{id}"),                          // Tool execution results
            "text-completion-request": request("text-completion:{id}"),   // LLM for tool reasoning
            "text-completion-response": response("text-completion:{id}"),
        },

    },

    // Class-level processors for agent-related services
    "class" +: {
    }
}