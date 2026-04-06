{

    // LLM model selection for normal LLM
    "llm-model": {
        "type": "llm-model",
        "description": "LLM model",
        "order": 1,
        "advanced": false,
    },

    // LLM model for RAG operations
    "llm-rag-model": {
        "type": "llm-model",
        "description": "LLM model for RAG",
        "order": 2,
        "advanced": true,
        "controlled-by": "llm-model",
    },

    // LLM model selection for normal LLM
    "llm-temperature": {
        "type": "llm-temperature",
        "description": "LLM temperature",
        "order": 3,
        "advanced": true,
    },

    // LLM model selection for normal LLM
    "llm-rag-temperature": {
        "type": "llm-temperature",
        "description": "LLM temperature for RAG",
        "order": 4,
        "advanced": true,
    },

    "embeddings-model": {
        "type": "embeddings-model",
        "description": "Embeddings model",
        "order": 5,
        "advanced": true,
    },

    // LLM model selection for normal LLM
    "chunk-size": {
        "type": "chunk-size",
        "description": "Chunk size",
        "order": 6,
        "advanced": true,
    },

    // LLM model selection for normal LLM
    "chunk-overlap": {
        "type": "chunk-overlap",
        "description": "Chunk overlap",
        "order": 7,
        "advanced": true,
    },

}
