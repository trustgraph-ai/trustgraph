// Mistral LLM Model Definitions
// Defines available models and their configurations for Mistral AI

{
    "type": "string",
    "description": "LLM model to use",
    "default": "mistral-medium-2508",
    "enum": [
        // Featured models
        {
            id: "mistral-medium-2508",
            description: "Mistral Medium 3.1"
        },
        {
            id: "mistral-large-2512",
            description: "Mistral Large 3"
        },
        {
            id: "mistral-small-2506",
            description: "Mistral Small 3.2"
        },
        {
            id: "ministral-14b-2512",
            description: "Ministral 3 14B"
        },
        {
            id: "ministral-8b-2512",
            description: "Ministral 3 8B"
        },
        {
            id: "ministral-3b-2512",
            description: "Ministral 3 3B"
        },
        {
            id: "magistral-medium-2509",
            description: "Magistral Medium 1.2 (reasoning)"
        },
        {
            id: "magistral-small-2509",
            description: "Magistral Small 1.2 (reasoning)"
        },
        {
            id: "devstral-2512",
            description: "Devstral 2 (code)"
        },
        // Other models
        {
            id: "codestral-2508",
            description: "Codestral (code)"
        },
        {
            id: "pixtral-large-2411",
            description: "Pixtral Large (vision)"
        },
        {
            id: "open-mistral-nemo",
            description: "Open Mistral Nemo"
        },
    ],
    "required": true
}
