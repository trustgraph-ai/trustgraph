// AWS Bedrock LLM Model Definitions
// Defines available models and their configurations for AWS Bedrock

{
    "type": "string",
    "description": "LLM model to use",
    "default": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "enum": [
        {
            id: "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
            description: "Claude Sonnet 4.5 (smartest for complex agents and coding)"
        },
        {
            id: "global.anthropic.claude-opus-4-5-20251101-v1:0",
            description: "Claude Opus 4.5 (maximum intelligence)"
        },
        {
            id: "global.anthropic.claude-haiku-4-5-20251001-v1:0",
            description: "Claude Haiku 4.5 (fastest with near-frontier intelligence)"
        },
        {
            id: "global.anthropic.claude-opus-4-1-20250805-v1:0",
            description: "Claude Opus 4.1 (specialized reasoning)"
        },
        {
            id: "global.anthropic.claude-sonnet-4-20250514-v1:0",
            description: "Claude Sonnet 4.0"
        },
        {
            id: "global.anthropic.claude-opus-4-20250514-v1:0",
            description: "Claude Opus 4.0"
        },
        {
            id: "anthropic.claude-3-5-haiku-20241022-v1:0",
            description: "Claude 3.5 Haiku"
        },
        {
            id: "anthropic.claude-3-haiku-20240307-v1:0",
            description: "Claude 3 Haiku"
        },
        {
            id: "meta.llama3-1-405b-instruct-v1:0",
            description: "Llama 3.1 405B Instruct"
        },
        {
            id: "meta.llama3-1-70b-instruct-v1:0",
            description: "Llama 3.1 70B Instruct"
        },
        {
            id: "meta.llama3-1-8b-instruct-v1:0",
            description: "Llama 3.1 8B Instruct"
        },
        {
            id: "mistral.mistral-large-2407-v1:0",
            description: "Mistral Large"
        },
        {
            id: "mistral.mixtral-8x7b-instruct-v0:1",
            description: "Mixtral 8x7B Instruct"
        },
    ],
    "required": true
}
