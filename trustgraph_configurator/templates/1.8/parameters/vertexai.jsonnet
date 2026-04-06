// VertexAI LLM Model Definitions
// Defines available models and their configurations for Google's VertexAI platform

{
    "type": "string",
    "description": "LLM model to use",
    "default": "gemini-2.5-flash-lite",
    "enum": [
        // Gemini 2.5 models (latest generation)
        {
            id: "gemini-2.5-pro",
            description: "Gemini 2.5 Pro"
        },
        {
            id: "gemini-2.5-flash",
            description: "Gemini 2.5 Flash"
        },
        {
            id: "gemini-2.5-flash-lite",
            description: "Gemini 2.5 Flash Lite"
        },

        // Gemini 2.0 models
        {
            id: "gemini-2.0-flash-exp",
            description: "Gemini 2.0 Flash (experimental)"
        },


        // Claude models on VertexAI
        {
            id: "claude-3-5-sonnet@20241022",
            description: "Claude 3.5 Sonnet (via VertexAI)"
        },
        {
            id: "claude-3-5-haiku@20241022",
            description: "Claude 3.5 Haiku (via VertexAI)"
        },
        {
            id: "claude-3-opus@20240229",
            description: "Claude 3 Opus (via VertexAI)"
        },
        {
            id: "claude-3-sonnet@20240229",
            description: "Claude 3 Sonnet (via VertexAI)"
        },
        {
            id: "claude-3-haiku@20240307",
            description: "Claude 3 Haiku (via VertexAI)"
        },

        // Llama models on VertexAI
        {
            id: "llama3-405b-instruct-maas",
            description: "Llama 3 405B Instruct (via VertexAI)"
        },
        {
            id: "llama3-70b-instruct-maas",
            description: "Llama 3 70B Instruct (via VertexAI)"
        },
        {
            id: "llama3-8b-instruct-maas",
            description: "Llama 3 8B Instruct (via VertexAI)"
        },
    ],
    "required": true
}

