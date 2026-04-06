// Chunk parameter type definitions

{
    "chunk-size": {
        "type": "integer",
        "description": "Chunk size",
        "placeholder": 2000,
        "helper": "An integer, usually 2000 .. 8000",
        "default": 2000,
        "min": 0,
        "max": 32768,
        "required": true
    },
    "chunk-overlap": {
        "type": "integer",
        "description": "Chunk overlap",
        "placeholder": 50,
        "helper": "An integer, usually 50 .. 100",
        "default": 50,
        "min": 0,
        "max": 8000,
        "required": true
    },
}

