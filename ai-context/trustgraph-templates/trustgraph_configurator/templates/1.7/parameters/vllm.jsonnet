// vLLM Model Definitions
// Defines available models and their configurations for vLLM
// vLLM works with any HuggingFace model, these are common optimized choices

{
    "type": "string",
    "description": "LLM model to use",
    "default": "meta-llama/Llama-3.1-8B-Instruct",
    "enum": [
        // Llama 3.1 models
        {
            id: "meta-llama/Llama-3.1-8B-Instruct",
            description: "Llama 3.1 8B Instruct"
        },
        {
            id: "meta-llama/Llama-3.1-70B-Instruct",
            description: "Llama 3.1 70B Instruct"
        },
        {
            id: "meta-llama/Llama-3.1-405B-Instruct",
            description: "Llama 3.1 405B Instruct"
        },

        // Llama 3.2 models
        {
            id: "meta-llama/Llama-3.2-1B-Instruct",
            description: "Llama 3.2 1B Instruct"
        },
        {
            id: "meta-llama/Llama-3.2-3B-Instruct",
            description: "Llama 3.2 3B Instruct"
        },

        // Qwen2.5 models
        {
            id: "Qwen/Qwen2.5-0.5B-Instruct",
            description: "Qwen2.5 0.5B Instruct"
        },
        {
            id: "Qwen/Qwen2.5-1.5B-Instruct",
            description: "Qwen2.5 1.5B Instruct"
        },
        {
            id: "Qwen/Qwen2.5-3B-Instruct",
            description: "Qwen2.5 3B Instruct"
        },
        {
            id: "Qwen/Qwen2.5-7B-Instruct",
            description: "Qwen2.5 7B Instruct"
        },
        {
            id: "Qwen/Qwen2.5-14B-Instruct",
            description: "Qwen2.5 14B Instruct"
        },
        {
            id: "Qwen/Qwen2.5-32B-Instruct",
            description: "Qwen2.5 32B Instruct"
        },
        {
            id: "Qwen/Qwen2.5-72B-Instruct",
            description: "Qwen2.5 72B Instruct"
        },

        // Mistral models
        {
            id: "mistralai/Mistral-7B-Instruct-v0.3",
            description: "Mistral 7B Instruct v0.3"
        },
        {
            id: "mistralai/Mixtral-8x7B-Instruct-v0.1",
            description: "Mixtral 8x7B Instruct"
        },
        {
            id: "mistralai/Mixtral-8x22B-Instruct-v0.1",
            description: "Mixtral 8x22B Instruct"
        },

        // Phi models
        {
            id: "microsoft/Phi-3.5-mini-instruct",
            description: "Phi 3.5 Mini Instruct"
        },
        {
            id: "microsoft/Phi-4",
            description: "Phi 4"
        },

        // Gemma models
        {
            id: "google/gemma-2-2b-it",
            description: "Gemma 2 2B Instruct"
        },
        {
            id: "google/gemma-2-9b-it",
            description: "Gemma 2 9B Instruct"
        },
        {
            id: "google/gemma-2-27b-it",
            description: "Gemma 2 27B Instruct"
        },

        // DeepSeek models
        {
            id: "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B",
            description: "DeepSeek-R1 Distill Qwen 1.5B"
        },
        {
            id: "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
            description: "DeepSeek-R1 Distill Qwen 7B"
        },
        {
            id: "deepseek-ai/DeepSeek-R1-Distill-Qwen-14B",
            description: "DeepSeek-R1 Distill Qwen 14B"
        },
        {
            id: "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B",
            description: "DeepSeek-R1 Distill Qwen 32B"
        },
        {
            id: "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
            description: "DeepSeek-R1 Distill Llama 70B"
        },
    ],
    "required": true
}
