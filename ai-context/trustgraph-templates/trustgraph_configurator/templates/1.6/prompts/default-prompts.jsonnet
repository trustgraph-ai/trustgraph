
// Prompt templates.  For tidy JSONNET use, don't change these templates
// here, but use over-rides in the prompt directory

{

    "system-template":: "You are a helpful assistant.",

    "templates":: {

        "question":: {
            "prompt": "{{question}}",
        },

        "extract-definitions":: {
            "prompt": "<instructions>\nStudy the following text and derive definitions for any discovered entities.\nDo not provide definitions for entities whose definitions are incomplete\nor unknown.\nOutput relationships in JSON format as an array of objects with fields:\n- entity: the name of the entity\n- definition: English text which defines the entity\n</instructions>\n\n<text>\n{{text}}\n</text>\n\n<requirements>\nYou will respond only with raw JSON format data. Do not provide\nexplanations. Do not use special characters in the abstract text. The\nabstract will be written as plain text.  Do not add markdown formatting\nor headers or prefixes.  Do not include null or unknown definitions.\n</requirements>",
            "response-type": "json",
            "schema": {
                "type": "array",
                "items": {
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
            }
        },

        "extract-relationships":: {
            "prompt": "<instructions>\nStudy the following text and derive entity relationships.  For each\nrelationship, derive the subject, predicate and object of the relationship.\nOutput relationships in JSON format as an array of objects with fields:\n- subject: the subject of the relationship\n- predicate: the predicate\n- object: the object of the relationship\n- object-entity: false if the object is a simple data type: name, value or date.  true if it is an entity.\n</instructions>\n\n<text>\n{{text}}\n</text>\n\n<requirements>\nYou will respond only with raw JSON format data. Do not provide\nexplanations. Do not use special characters in the abstract text. The\nabstract must be written as plain text.  Do not add markdown formatting\nor headers or prefixes.\n</requirements>",
            "response-type": "json",
            "schema": {
                "type": "array",
                "items": {
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
                        },
                    },
                    "required": [
                        "subject",
                        "predicate",
                        "object",
                        "object-entity"
                    ]
                }
            }
        },

        "extract-topics":: {
            "prompt": "You are a helpful assistant that performs information extraction tasks for a provided text.\nRead the provided text. You will identify topics and their definitions in JSON.\n\nReading Instructions:\n- Ignore document formatting in the provided text.\n- Study the provided text carefully.\n\nHere is the text:\n{{text}}\n\nResponse Instructions: \n- Do not respond with special characters.\n- Return only topics that are concepts and unique to the provided text.\n- Respond only with well-formed JSON.\n- The JSON response shall be an array of objects with keys \"topic\" and \"definition\". \n- The JSON response shall use the following structure:\n\n```json\n[{\"topic\": string, \"definition\": string}]\n```\n\n- Do not write any additional text or explanations.",
            "response-type": "json",
            "schema": {
                "type": "array",
                "items": {
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
            }
        },

        "extract-rows":: {
            "prompt": "<instructions>\nStudy the following text and derive objects which match the schema provided.\n\nYou must output an array of JSON objects for each object you discover\nwhich matches the schema.  For each object, output a JSON object whose fields\ncarry the name field specified in the schema.\n</instructions>\n\n<schema>\n{{schema}}\n</schema>\n\n<text>\n{{text}}\n</text>\n\n<requirements>\nYou will respond only with raw JSON format data. Do not provide\nexplanations. Do not add markdown formatting or headers or prefixes.\n</requirements>",
            "response-type": "json",
        },

        "kg-prompt":: {
            "prompt": "Study the following set of knowledge statements. The statements are written in Cypher format that has been extracted from a knowledge graph. Use only the provided set of knowledge statements in your response. Do not speculate if the answer is not found in the provided set of knowledge statements.\n\nHere's the knowledge statements:\n{% for edge in knowledge %}({{edge.s}})-[{{edge.p}}]->({{edge.o}})\n{%endfor%}\n\nUse only the provided knowledge statements to respond to the following:\n{{query}}\n",
            "response-type": "text",
        },

        "document-prompt":: {
            "prompt": "Study the following context. Use only the information provided in the context in your response. Do not speculate if the answer is not found in the provided set of knowledge statements.\n\nHere is the context:\n{{documents}}\n\nUse only the provided knowledge statements to respond to the following:\n{{query}}\n",
            "response-type": "text",
        },

        "agent-react":: {
            "prompt": importstr "agent-prompt.txt",
            "response-type": "text"
        },

        "agent-kg-extract":: {
            "prompt": "Analyze the following text and extract both entity definitions and relationships. Return the results as JSON with 'definitions' and 'relationships' arrays.\n\nFor definitions, extract entities and their explanations or descriptions.\nFor relationships, extract subject-predicate-object triples where subjects and objects are entities, and predicates are relationship types.\n\nText: {{text}}\n\nReturn JSON only, no other text. Use this exact format:\n{\n  \"definitions\": [\n    {\n      \"entity\": \"entity_name\",\n      \"definition\": \"definition_text\"\n    }\n  ],\n  \"relationships\": [\n    {\n      \"subject\": \"subject_entity\",\n      \"predicate\": \"relationship_type\",\n      \"object\": \"object_entity_or_literal\",\n      \"object-entity\": true\n    }\n  ]\n}\n",
            "response-type": "json",
            "schema": {
                "type": "object",
                "properties": {
                    "definitions": {
                        "type": "array",
                        "items": {
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
                    "relationships": {
                        "type": "array",
                        "items": {
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
                                "object"
                            ]
                        }
                    }
                },
                "required": [
                    "definitions",
                    "relationships"
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
            "response-type": "json",
        },

    }

}

