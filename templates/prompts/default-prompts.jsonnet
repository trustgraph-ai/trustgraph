
// Prompt templates.  For tidy JSONNET use, don't change these templates
// here, but use over-rides in the prompt directory

{

    "system-template":: "You are a helpful assistant.",

    "templates":: {

        "question":: {
            "prompt": "{{question}}",
        },

        "extract-definitions":: {
            "prompt": "<instructions>\nStudy the following text and derive definitions for any discovered entities.\nDo not provide definitions for entities whose definitions are incomplete\nor unknown.\nOutput relationships in JSON format as an arary of objects with fields:\n- entity: the name of the entity\n- definition: English text which defines the entity\n</instructions>\n\n<text>\n{{text}}\n</text>\n\n<requirements>\nYou will respond only with raw JSON format data. Do not provide\nexplanations. Do not use special characters in the abstract text. The\nabstract will be written as plain text.  Do not add markdown formatting\nor headers or prefixes.  Do not include null or unknown definitions.\n</requirements>",
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
            "prompt": "<instructions>\nStudy the following text and derive entity relationships.  For each\nrelationship, derive the subject, predicate and object of the relationship.\nOutput relationships in JSON format as an arary of objects with fields:\n- subject: the subject of the relationship\n- predicate: the predicate\n- object: the object of the relationship\n- object-entity: false if the object is a simple data type: name, value or date.  true if it is an entity.\n</instructions>\n\n<text>\n{{text}}\n</text>\n\n<requirements>\nYou will respond only with raw JSON format data. Do not provide\nexplanations. Do not use special characters in the abstract text. The\nabstract must be written as plain text.  Do not add markdown formatting\nor headers or prefixes.\n</requirements>",
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
            "prompt": "Answer the following questions as best you can. You have\naccess to the following functions:\n\n{% for tool in tools %}{\n    \"function\": \"{{ tool.name }}\",\n    \"description\": \"{{ tool.description }}\",\n    \"arguments\": [\n{% for arg in tool.arguments %}        {\n            \"name\": \"{{ arg.name }}\",\n            \"type\": \"{{ arg.type }}\",\n            \"description\": \"{{ arg.description }}\",\n        }\n{% endfor %}\n    ]\n}\n{% endfor %}\n\nYou can either choose to call a function to get more information, or\nreturn a final answer.\n    \nTo call a function, respond with a JSON object of the following format:\n\n{\n    \"thought\": \"your thought about what to do\",\n    \"action\": \"the action to take, should be one of [{{tool_names}}]\",\n    \"arguments\": {\n        \"argument1\": \"argument_value\",\n        \"argument2\": \"argument_value\"\n    }\n}\n\nTo provide a final answer, response a JSON object of the following format:\n\n{\n  \"thought\": \"I now know the final answer\",\n  \"final-answer\": \"the final answer to the original input question\"\n}\n\nPrevious steps are included in the input.  Each step has the following\nformat in your output:\n\n{\n  \"thought\": \"your thought about what to do\",\n  \"action\": \"the action taken\",\n  \"arguments\": {\n      \"argument1\": action argument,\n      \"argument2\": action argument2\n  },\n  \"observation\": \"the result of the action\",\n}\n\nRespond by describing either one single thought/action/arguments or\nthe final-answer.  Pause after providing one action or final-answer.\n\n{% if context %}Additional context has been provided:\n{{context}}{% endif %}\n\nQuestion: {{question}}\n\nInput:\n    \n{% for h in history %}\n{\n    \"action\": \"{{h.action}}\",\n    \"arguments\": [\n{% for k, v in h.arguments.items() %}        {\n            \"{{k}}\": \"{{v}}\",\n{%endfor%}        }\n    ],\n    \"observation\": \"{{h.observation}}\"\n}\n{% endfor %}",
            "response-type": "json"
        }
    }

}

