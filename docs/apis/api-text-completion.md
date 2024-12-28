
# TrustGraph Embeddings API

## Request/response

### Request

Some LLM system permit specifying a separate `system` prompt.  When
the same system prompt is used repeatedly, this can result in lower
token costs for the system part or quicker LLM response.

The request contains the following fields:
- `system`: A string, the system part
- `prompt`: A string, the user part

### Response

The request contains the following fields:
- `response`: LLM response

## REST service

The REST service accepts a request object containing the question field.
The response is a JSON object containing the `answer` field.  Interim
responses are not provided.

e.g.

Request:
```
{
    "system": "You are a helpful agent",
    "prompt": "What does NASA stand for?"
}
```

Response:

```
{
    "response": "National Aeronautics and Space Administration"
}
```

## Websocket

Agent requests have a `request` object containing the `system` and
`prompt` fields.
Responses have a `response` object containing `response` field.

e.g.

Request:

```

{
    "id": "blrqotfefnmnh7de-1",
    "service": "text-completion",
    "request": {
        "system": "You are a helpful agent",
        "prompt": "What does NASA stand for?"
    }
}
```

Responses:

```


{
    "id": "blrqotfefnmnh7de-1",
    "response": {
        "response": "National Aeronautics and Space Administration"
    },
    "complete": true
}
```

## Pulsar

The Pulsar schema for the Agent API is defined in Python code here:

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/schema/models.py

Default request queue:
`non-persistent://tg/request/text-completion`

Default response queue:
`non-persistent://tg/response/text-completion`

Request schema:
`trustgraph.schema.TextCompletionRequest`

Response schema:
`trustgraph.schema.TextCompletionResponse`

## Pulsar Python client

The client class is
`trustgraph.clients.LlmClient`

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/clients/llm_client.py

