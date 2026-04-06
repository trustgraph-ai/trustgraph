// Embeddings model definitions for fastembed
// Defines available models and their configurations for Fastembed

{
    "type": "string",
    "description": "Embeddings model to use",
    "default": "sentence-transformers/all-MiniLM-L6-v2",
    "enum": [
	{
	    "id": "all-MiniLM-L6-v2",
	    "description": "all-MiniLM-L6-v2"
	},
	{
	    "id": "all-mpnet-base-v2",
	    "description": "all-mpnet-base-v2"
	},
	{
	    "id": "all-distilroberta-v1",
	    "description": "all-distilroberta-v1"
	},
	{
	    "id": "stsb-bert-large",
	    "description": "stsb-bert-large"
	},
	{
	    "id": "sentence-camembert-large",
	    "description": "sentence-camembert-large"
	}
    ],
    "required": true
}
