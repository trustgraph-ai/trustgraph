// OpenAI LLM Model Definitions
// Defines available models and their configurations for OpenAI's platform

{
    "type": "string",
    "description": "LLM model to use",
    "default": "gpt-5.2",
    "enum": [
        {
            id: "gpt-5.2-pro",
            description: "GPT-5.2 Pro (maximum intelligence, slow)"
        },
        {
            id: "gpt-5.2",
            description: "GPT-5.2 (flagship, best general-purpose)"
        },
        {
            id: "gpt-5.2-codex",
            description: "GPT-5.2 Codex (optimized for agentic coding)"
        },
        {
            id: "gpt-5.1",
            description: "GPT-5.1 (previous flagship)"
        },
        {
            id: "gpt-5",
            description: "GPT-5 (previous gen reasoning)"
        },
        {
            id: "gpt-4.1",
            description: "GPT-4.1 (coding + long context, 1M tokens)"
        },
        {
            id: "gpt-4.1-mini",
            description: "GPT-4.1 Mini (fast + affordable)"
        },
        {
            id: "gpt-4.1-nano",
            description: "GPT-4.1 Nano (ultra-fast, cheapest)"
        },
        {
            id: "gpt-4o",
            description: "GPT-4o (legacy multimodal)"
        },
        {
            id: "gpt-4o-mini",
            description: "GPT-4o Mini (legacy, budget)"
        },
    ],
    "required": true
}