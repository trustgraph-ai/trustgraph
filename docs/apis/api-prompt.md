
# TrustGraph Prompt API

This is a higher-level interface to the LLM service.  The input
specifies a prompt template by ID and some variables to include in the
template.

## Request/response

### Request

The request contains the following fields:
- `id`: A prompt template ID
- `variables`: A set of key/values describing the variables

### Response

The response contains either of these fields:
- `text`: A plain text response
- `object`: A structured object, JSON-encoded

## REST service

The REST service accepts `id` and `variables` fields, the variables are
encoded as a JSON object.

e.g.

In this example, the template takes a `text` variable and returns an
array of entity definitions in t he `object` field.  The value is
JSON-encoded.

Request:
```
{
    "id": "extract-definitions",
    "variables": {
        "text": "A cat is a domesticated Felidae animal"
    }
}
```

Response:

```
{
    "object": "[{\"entity\": \"cat\", \"definition\": \"a domesticated Felidae animal\"}]"
},
```

## Websocket

Requests have `id` and `variables` fields.

e.g.

Request:

```
{
    "id": "akshfkiehfkseffh-142",
    "service": "prompt",
    "flow": "default",
    "request": {
        "id": "extract-definitions",
        "variables": {
            "text": "A cat is a domesticated Felidae animal"
        }
    }
}
```

Responses:

```
{
    "id": "akshfkiehfkseffh-142",
    "response": {
        "object": "[{\"entity\": \"cat\", \"definition\": \"a domesticated Felidae animal\"}]"
    },
    "complete": true
}
```

e.g.

An example which returns plain text

Request:

```
{
    "id": "akshfkiehfkseffh-141",
    "service": "prompt",
    "request": {
        "id": "question",
        "variables": {
            "question": "What is 2 + 2?"
        }
    }
}
```

Response:

```
{
    "id": "akshfkiehfkseffh-141",
    "response": {
        "text": "2 + 2 = 4"
    },
    "complete": true
}
```


## Pulsar

The Pulsar schema for the Prompt API is defined in Python code here:

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/schema/prompt.py

Default request queue:
`non-persistent://tg/request/prompt`

Default response queue:
`non-persistent://tg/response/prompt`

Request schema:
`trustgraph.schema.PromptRequest`

Response schema:
`trustgraph.schema.PromptResponse`

## Pulsar Python client

The client class is
`trustgraph.clients.PromptClient`

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/clients/prompt_client.py

