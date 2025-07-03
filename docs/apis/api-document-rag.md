# TrustGraph Document RAG API

This presents a prompt to the Document RAG service and retrieves the answer.
This makes use of a number of the other APIs behind the scenes:
Embeddings, Document Embeddings, Prompt, TextCompletion, Triples Query.

## Request/response

### Request

The request contains the following fields:
- `query`: The question to answer

### Response

The response contains the following fields:
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
    "service": "document-rag",
    "flow": "default",
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

The Pulsar schema for the Document RAG API is defined in Python code here:

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/schema/retrieval.py

Default request queue:
`non-persistent://tg/request/document-rag`

Default response queue:
`non-persistent://tg/response/document-rag`

Request schema:
`trustgraph.schema.DocumentRagQuery`

Response schema:
`trustgraph.schema.DocumentRagResponse`

## Pulsar Python client

The client class is
`trustgraph.clients.DocumentRagClient`

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/clients/document_rag_client.py