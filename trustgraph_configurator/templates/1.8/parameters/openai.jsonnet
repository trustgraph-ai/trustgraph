// OpenAI LLM Model Definitions
// Defines available models and their configurations for OpenAI's platform

{
    "type": "string",
    "description": "LLM model to use",
    "default": "gpt-4o",
    "enum": [
        {
            id: "gpt-4o",
            description: "GPT-4o (latest)"
        },
        {
            id: "gpt-4o-mini",
            description: "GPT-4o Mini"
        },
        {
            id: "gpt-4-turbo",
            description: "GPT-4 Turbo"
        },
        {
            id: "gpt-4",
            description: "GPT-4"
        },
        {
            id: "gpt-3.5-turbo",
            description: "GPT-3.5 Turbo"
        },
    ],
    "required": true
}