// Tools Configuration Module
// Defines all available tools that can be used by agents and flows
// Each tool specifies its interface, arguments, and behavior

[
    // Knowledge query tool - queries the knowledge base
    {
        id: "knowledge-query",
        name: "Knowledge query",
        description: "This tool queries a knowledge base that holds information about domain-specific information. The question should be a natural language question.",
        type: "knowledge-query",
        collection: "default",
        arguments: [
            {
                name: "question",
                type: "string",
                description: "A simple natural language question.",
            }
        ]
    },

    // LLM completion tool - general purpose text completion
    {
        id: "llm-completion",
        name: "LLM text completion",
        type: "text-completion",
        description: "This tool queries an LLM for non-domain-specific information. The question should be a natural language question.",
        arguments: [
            {
                name: "question",
                type: "string",
                description: "The question which should be asked of the LLM.",
            }
        ]
    }
]