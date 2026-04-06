// Cohere LLM Model Definitions
// Defines available models and their configurations for Cohere

{
    "type": "string",
    "description": "LLM model to use",
    "default": "command-r-plus-08-2024",
    "enum": [
        {
            id: "command-r-plus-08-2024",
            description: "Command R+ (August 2024)"
        },
        {
            id: "command-r-08-2024",
            description: "Command R (August 2024)"
        },
        {
            id: "command-r-plus",
            description: "Command R+ (legacy)"
        },
        {
            id: "command-r",
            description: "Command R (legacy)"
        },
        {
            id: "command",
            description: "Command"
        },
        {
            id: "command-light",
            description: "Command Light"
        },
    ],
    "required": true
}
