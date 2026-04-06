// Google AI Studio LLM Model Definitions
// Defines available models and their configurations for Google AI Studio

{
    "type": "string",
    "description": "LLM model to use",
    "default": "gemini-2.5-flash-lite",
    "enum": [
        // Gemini 3 models (preview)
        {
            id: "gemini-3-pro-preview",
            description: "Gemini 3 Pro (preview)"
        },
        {
            id: "gemini-3-flash-preview",
            description: "Gemini 3 Flash (preview)"
        },

        // Gemini 2.5 models
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
            id: "gemini-2.0-flash-001",
            description: "Gemini 2.0 Flash"
        },
        {
            id: "gemini-2.0-flash-lite-001",
            description: "Gemini 2.0 Flash Lite"
        },

        // Gemma models
        {
            id: "gemma-3-27b",
            description: "Gemma 3 27B"
        },
        {
            id: "gemma-3n-e4b",
            description: "Gemma 3n E4B"
        },
    ],
    "required": true
}
