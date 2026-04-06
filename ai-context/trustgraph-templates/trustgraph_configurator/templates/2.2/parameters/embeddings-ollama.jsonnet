// Embeddings model definitions for Ollama
// Defines available models and their configurations for Ollama

{
    "type": "string",
    "description": "Embeddings model to use",
    "default": "all-minilm:latest",
    "enum": [
	{
	    "id": "all-minilm:latest",
	    "description": "all-MiniLM-L6-v2"
	},
	{
	    "id": "nomic-ai/nomic-embed-text-v1.5-Q",
	    "description": "nomic-embed-text-v1.5-Q"
	},
	{
	    "id": "mixedbread-ai/mxbai-embed-large-v1",
	    "description": "mxbai-embed-large-v1"
	},
    ],
    "required": true
}
