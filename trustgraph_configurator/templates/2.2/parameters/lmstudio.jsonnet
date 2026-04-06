// LMStudio LLM Model Definitions
// Defines available models and their configurations for LMStudio

{
    "type": "string",
    "description": "LLM model to use",
    "default": "llama3.1:70b",
    "enum": [
        // Gemma3 models
        {
            id: "gemma3:1b",
            description: "Gemma3 1B"
        },
        {
            id: "gemma3:4b",
            description: "Gemma3 4B"
        },
        {
            id: "gemma3:12b",
            description: "Gemma3 12B"
        },
        {
            id: "gemma3:27b",
            description: "Gemma3 27B"
        },

        // Phi4 models
        {
            id: "phi4:mini:3.8b",
            description: "Phi4 Mini 3.8B"
        },
        {
            id: "phi4:14b",
            description: "Phi4 14B"
        },

        // DeepSeek-R1 models
        {
            id: "deepseek-r1:671b",
            description: "DeepSeek-R1 671B"
        },
        {
            id: "deepseek-r1:70b",
            description: "DeepSeek-R1 70B"
        },
        {
            id: "deepseek-r1:32b",
            description: "DeepSeek-R1 32B"
        },
        {
            id: "deepseek-r1:14b",
            description: "DeepSeek-R1 14B"
        },
        {
            id: "deepseek-r1:8b",
            description: "DeepSeek-R1 8B"
        },
        {
            id: "deepseek-r1:7b",
            description: "DeepSeek-R1 7B"
        },
        {
            id: "deepseek-r1:1.5b",
            description: "DeepSeek-R1 1.5B"
        },

        // Llama3.1 models
        {
            id: "llama3.1:405b",
            description: "Llama 3.1 405B"
        },
        {
            id: "llama3.1:70b",
            description: "Llama 3.1 70B"
        },
        {
            id: "llama3.1:8b",
            description: "Llama 3.1 8B"
        },

        // Gemma2 models
        {
            id: "gemma2:2b",
            description: "Gemma2 2B"
        },
        {
            id: "gemma2:9b",
            description: "Gemma2 9B"
        },
        {
            id: "gemma2:27b",
            description: "Gemma2 27B"
        },

        // Qwen2.5 models
        {
            id: "qwen2.5:0.5b",
            description: "Qwen2.5 0.5B"
        },
        {
            id: "qwen2.5:1.5b",
            description: "Qwen2.5 1.5B"
        },
        {
            id: "qwen2.5:3b",
            description: "Qwen2.5 3B"
        },
        {
            id: "qwen2.5:7b",
            description: "Qwen2.5 7B"
        },
        {
            id: "qwen2.5:14b",
            description: "Qwen2.5 14B"
        },
        {
            id: "qwen2.5:32b",
            description: "Qwen2.5 32B"
        },
        {
            id: "qwen2.5:72b",
            description: "Qwen2.5 72B"
        },

        // Mistral models
        {
            id: "mistral:7b",
            description: "Mistral 7B"
        },
        {
            id: "mistral-nemo:12b",
            description: "Mistral Nemo 12B"
        },
        {
            id: "mistral-large:123b",
            description: "Mistral Large 123B"
        },

        // Command-R models
        {
            id: "command-r:35b",
            description: "Command-R 35B"
        },
        {
            id: "command-r-plus:104b",
            description: "Command-R Plus 104B"
        },
    ],
    "required": true
}