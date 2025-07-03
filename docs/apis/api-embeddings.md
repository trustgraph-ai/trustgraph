
# TrustGraph Embeddings API

## Request/response

### Request

The request contains the following fields:
- `text`: A string, the text to apply the embedding to

### Response

The response contains the following fields:
- `vectors`: Embeddings response, an array of arrays.  An embedding is
  an array of floating-point numbers.  As multiple embeddings may be
  returned, an array of embeddings is returned, hence an array
  of arrays.

## REST service

The REST service accepts a request object containing the question field.
The response is a JSON object containing the `answer` field.

e.g.

Request:
```
{
    "text": "What does NASA stand for?"
}
```

Response:

```
{
    "vectors": [ 0.231341245, ... ]
}
```

## Websocket

Embeddings requests have a `request` object containing the `text` field.
Responses have a `response` object containing `vectors` field.

e.g.

Request:

```
{
    "id": "qgzw1287vfjc8wsk-2",
    "service": "embeddings",
    "flow": "default",
    "request": {
        "text": "What is a cat?"
    }
}
```

Responses:

```


{
    "id": "qgzw1287vfjc8wsk-2",
    "response": {
        "vectors": [
            [
                0.04013510048389435,
                0.07536131888628006,
                ...
                -0.023531345650553703,
                0.03591292351484299
            ]
        ]
    },
    "complete": true
}
```

## Pulsar

The Pulsar schema for the Embeddings API is defined in Python code here:

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/schema/models.py

Default request queue:
`non-persistent://tg/request/embeddings`

Default response queue:
`non-persistent://tg/response/embeddings`

Request schema:
`trustgraph.schema.EmbeddingsRequest`

Response schema:
`trustgraph.schema.EmbeddingsResponse`

## Pulsar Python client

The client class is
`trustgraph.clients.EmbeddingsClient`

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/clients/embeddings_client.py

