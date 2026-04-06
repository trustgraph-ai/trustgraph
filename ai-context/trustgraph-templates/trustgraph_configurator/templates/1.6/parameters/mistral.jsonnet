// Mistral LLM Model Definitions
// Defines available models and their configurations for Mistral AI

{
    "type": "string",
    "description": "LLM model to use",
    "default": "mistral-large-latest",
    "enum": [
        {
            id: "mistral-large-latest",
            description: "Mistral Large (latest)"
        },
        {
            id: "mistral-medium-latest",
            description: "Mistral Medium (latest)"
        },
        {
            id: "mistral-small-latest",
            description: "Mistral Small (latest)"
        },
        {
            id: "open-mistral-nemo",
            description: "Open Mistral Nemo"
        },
        {
            id: "open-mistral-7b",
            description: "Open Mistral 7B"
        },
        {
            id: "open-mixtral-8x7b",
            description: "Open Mixtral 8x7B"
        },
        {
            id: "open-mixtral-8x22b",
            description: "Open Mixtral 8x22B"
        },
    ],
    "required": true
}
