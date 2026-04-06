// AWS Bedrock LLM Model Definitions
// Defines available models and their configurations for AWS Bedrock

{
    "type": "string",
    "description": "LLM model to use",
    "default": "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "enum": [
        // ── Anthropic Claude ──────────────────────────────────────
        {
            id: "global.anthropic.claude-opus-4-6-v1",
            description: "Claude Opus 4.6 (maximum intelligence)"
        },
        {
            id: "global.anthropic.claude-opus-4-5-20251101-v1:0",
            description: "Claude Opus 4.5 (frontier coding + agents)"
        },
        {
            id: "global.anthropic.claude-sonnet-4-5-20250929-v1:0",
            description: "Claude Sonnet 4.5 (complex agents + coding)"
        },
        {
            id: "global.anthropic.claude-haiku-4-5-20251001-v1:0",
            description: "Claude Haiku 4.5 (fastest with near-frontier intelligence)"
        },
        {
            id: "global.anthropic.claude-opus-4-1-20250805-v1:0",
            description: "Claude Opus 4.1 (agentic search + reasoning)"
        },
        {
            id: "global.anthropic.claude-sonnet-4-20250514-v1:0",
            description: "Claude Sonnet 4.0"
        },
        {
            id: "anthropic.claude-3-5-haiku-20241022-v1:0",
            description: "Claude 3.5 Haiku (legacy)"
        },

        // ── Meta Llama ────────────────────────────────────────────
        {
            id: "us.meta.llama4-maverick-17b-instruct-v1:0",
            description: "Llama 4 Maverick 17B (128 experts, 400B params, multimodal)"
        },
        {
            id: "us.meta.llama4-scout-17b-instruct-v1:0",
            description: "Llama 4 Scout 17B (16 experts, 3.5M context)"
        },
        {
            id: "us.meta.llama3-3-70b-instruct-v1:0",
            description: "Llama 3.3 70B Instruct"
        },

        // ── Mistral AI ────────────────────────────────────────────
        {
            id: "us.mistral.mistral-large-2511-v1:0",
            description: "Mistral Large 3 (flagship text, 128K context)"
        },
        {
            id: "us.mistral.magistral-small-2506-v1:0",
            description: "Magistral Small 1.2 (reasoning, cost-effective)"
        },

        // ── DeepSeek ──────────────────────────────────────────────
        {
            id: "us.deepseek.r1-v1:0",
            description: "DeepSeek-R1 (reasoning)"
        },

        // ── Amazon Nova ───────────────────────────────────────────
        {
            id: "us.amazon.nova-pro-v1:0",
            description: "Amazon Nova Pro (multimodal, balanced)"
        },
        {
            id: "us.amazon.nova-lite-v1:0",
            description: "Amazon Nova Lite (fast, multimodal)"
        },
        {
            id: "us.amazon.nova-micro-v1:0",
            description: "Amazon Nova Micro (text-only, cheapest)"
        },
    ],
    "required": true
}
