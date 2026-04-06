
// Prompt templates.  For tidy JSONNET use, don't change these templates
// here, but use over-rides in the prompt directory

{

    "system-template":: "You are a helpful assistant.",

    "templates":: {

        "question":: {
            "prompt": "{{question}}",
        },

        "extract-definitions":: {
            "prompt": importstr "extract-definitions.txt",
            "response-type": "jsonl",
            "object-schema": {
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string"
                    },
                    "definition": {
                        "type": "string"
                    }
                },
                "required": [
                    "entity",
                    "definition"
                ]
            }
        },

        "extract-relationships":: {
            "prompt": importstr "extract-relationships.txt",
            "response-type": "jsonl",
            "object-schema": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string"
                    },
                    "predicate": {
                        "type": "string"
                    },
                    "object": {
                        "type": "string"
                    },
                    "object-entity": {
                        "type": "boolean"
                    }
                },
                "required": [
                    "subject",
                    "predicate",
                    "object",
                    "object-entity"
                ]
            }
        },

        "extract-topics":: {
            "prompt": importstr "extract-topics.txt",
            "response-type": "jsonl",
            "object-schema": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string"
                    },
                    "definition": {
                        "type": "string"
                    }
                },
                "required": [
                    "topic",
                    "definition"
                ]
            }
        },

        "extract-rows":: {
            "prompt": importstr "extract-rows.txt",
            "response-type": "jsonl",
        },

        "kg-prompt":: {
            "prompt": importstr "kg-prompt.txt",
            "response-type": "text",
        },

        "document-prompt":: {
            "prompt": importstr "document-prompt.txt",
            "response-type": "text",
        },

        "agent-react":: {
            "prompt": importstr "agent-prompt.txt",
            "response-type": "text"
        },

        "agent-kg-extract":: {
            "prompt": importstr "agent-kg-extract.txt",
            "response-type": "jsonl",
            "object-schema": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "type": { "const": "definition" },
                            "entity": { "type": "string" },
                            "definition": { "type": "string" }
                        },
                        "required": ["type", "entity", "definition"]
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": { "const": "relationship" },
                            "subject": { "type": "string" },
                            "predicate": { "type": "string" },
                            "object": { "type": "string" },
                            "object-entity": { "type": "boolean" }
                        },
                        "required": ["type", "subject", "predicate", "object"]
                    }
                ]
            }
        },

        "schema-selection":: {
            "prompt": importstr "schema-selection.txt",
            "response-type": "json",
            "schema": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "An array of schema names that are relevant to answering the given question"
            }
        },

        "graphql-generation":: {
            "prompt": importstr "graphql-generation.txt",
            "response-type": "json",
            "schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The GraphQL query string generated to answer the question"
                    },
                    "variables": {
                        "type": "object",
                        "description": "Object containing any GraphQL variables needed for the query",
                        "additionalProperties": true
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Float between 0.0-1.0 indicating confidence in the generated query"
                    }
                },
                "required": ["query", "variables", "confidence"],
                "additionalProperties": false
            }
        },

        "diagnose-structured-data":: {
            "prompt": importstr "diagnose-structured-data.txt",
            "response-type": "json",
        },

        "diagnose-xml":: {
            "prompt": importstr "diagnose-xml.txt",
            "response-type": "json",
        },
        "diagnose-json":: {
            "prompt": importstr "diagnose-json.txt",
            "response-type": "json",
        },
        "diagnose-csv":: {
            "prompt": importstr "diagnose-csv.txt",
            "response-type": "json",
        },

        "extract-with-ontologies":: {
            "prompt": importstr "ontology-prompt.txt",
            "response-type": "jsonl",
            "object-schema": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "type": { "const": "entity" },
                            "entity": { "type": "string" },
                            "entity_type": { "type": "string" }
                        },
                        "required": ["type", "entity", "entity_type"]
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": { "const": "relationship" },
                            "subject": { "type": "string" },
                            "subject_type": { "type": "string" },
                            "relation": { "type": "string" },
                            "object": { "type": "string" },
                            "object_type": { "type": "string" }
                        },
                        "required": ["type", "subject", "subject_type", "relation", "object", "object_type"]
                    },
                    {
                        "type": "object",
                        "properties": {
                            "type": { "const": "attribute" },
                            "entity": { "type": "string" },
                            "entity_type": { "type": "string" },
                            "attribute": { "type": "string" },
                            "value": { "type": "string" }
                        },
                        "required": ["type", "entity", "entity_type", "attribute", "value"]
                    }
                ]
            }
        },

    }

}

