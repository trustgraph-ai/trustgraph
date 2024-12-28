
# TrustGraph Graph RAG API

This presents a prompt to the Graph RAG service and retrieves the answer.
This makes use of a number of the other APIs behind the scenes:
Embeddings, Graph Embeddings, Prompt, TextCompletion, Triples Query.

## Request/response

### Request

The request contains the following fields:
- `query`: The question to answer

### Response

The request contains the following fields:
- `response`: LLM response

## REST service

The REST service accepts a request object containing the `query` field.
The response is a JSON object containing the `response` field.

e.g.

Request:
```
{
    "query": "What does NASA stand for?"
}
```

Response:

```
{
    "response": "National Aeronautics and Space Administration"
}
```

## Websocket

Requests have a `request` object containing the `query` field.
Responses have a `response` object containing `response` field.

e.g.

Request:

```
{
    "id": "blrqotfefnmnh7de-14",
    "service": "graph-rag",
    "request": {
        "query": "What does NASA stand for?"
    }
}
```

Response:

```
{
    "id": "blrqotfefnmnh7de-14",
    "response": {
        "response": "National Aeronautics and Space Administration"
    },
    "complete": true
}
```

## Pulsar

The Pulsar schema for the Graph RAG API is defined in Python code here:

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/schema/retrieval.py

Default request queue:
`non-persistent://tg/request/graph-rag`

Default response queue:
`non-persistent://tg/response/graph-rag`

Request schema:
`trustgraph.schema.GraphRagRequest`

Response schema:
`trustgraph.schema.GraphRagResponse`

## Pulsar Python client

The client class is
`trustgraph.clients.GraphRagClient`

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/clients/graph_rag_client.py







{"id":"as9trkhb9jtizjio-1","service":"graph-rag","request":{"query":"What does NASA stand for?"}}


{"id": "as9trkhb9jtizjio-1", "response": {"response": "Based on the provided text, NASA stands for National Aeronautics and Space Administration.  There are multiple statements providing this definition.\n"}, "complete": true}

