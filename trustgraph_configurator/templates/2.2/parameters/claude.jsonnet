// Claude LLM Model Definitions
// Defines available models and their configurations for Anthropic's Claude

{
    "type": "string",
    "description": "LLM model to use",
    "default": "claude-sonnet-4-5-20250929",
    "enum": [
        {
            id: "claude-opus-4-6",
            description: "Claude Opus 4.6 (maximum intelligence)"
        },
        {
            id: "claude-opus-4-5-20251101",
            description: "Claude Opus 4.5 (frontier coding + agents)"
        },
        {
            id: "claude-sonnet-4-5-20250929",
            description: "Claude Sonnet 4.5 (complex agents + coding)"
        },
        {
            id: "claude-haiku-4-5-20251001",
            description: "Claude Haiku 4.5 (fast)"
        },
        {
            id: "claude-opus-4-1-20250805",
            description: "Claude Opus 4.1 (agentic search + reasoning)"
        },
        {
            id: "claude-sonnet-4-20250514",
            description: "Claude Sonnet 4.0"
        },
        {
            id: "claude-3-5-haiku-20241022",
            description: "Claude 3.5 Haiku"
        },
    ],
    "required": true
}
