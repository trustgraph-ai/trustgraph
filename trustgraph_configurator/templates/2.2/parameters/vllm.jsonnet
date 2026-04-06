// vLLM Model Definitions
// Defines available models and their configurations for vLLM
// vLLM works with any HuggingFace model.  We have to use the model
// vLLM was initialised with

{
    "type": "string",
    "description": "LLM model to use",
    "default": "model",
    "enum": [
        // Llama 3.1 models
        {
            id: "model",
            description: "Pre-defined model"
        },
    ],
    "required": true
}
