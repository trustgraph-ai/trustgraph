
# TrustGraph Graph Embeddings API

The purpose of this API is to search for knowledge graph entities
by embeddings.  The request is a list of embeddings, the response is
a list of knowledge graph entities.  The search is performed using a
vector store.

## Request/response

### Request

The request contains the following fields:
- `vectors`: An array of embeddings.  Each embedding is itself an array
   of numbers.
- `limit`: Optional: a limit on the number of graph entities to return.

### Response

The response contains the following fields:
- `entities`: An array of graph entities.  The entity type is described here:

TrustGraph uses the same schema for knowledge graph elements:
- `value`: the entity URI or literal value depending on whether this is
  graph entity or literal value.
- `is_uri`: A boolean value which is true if this is a graph entity i.e.
  `value` is a URI, not a literal value.

## REST service

The REST service accepts a request object containing the `vectors` field.
The response is a JSON object containing the `entities` field.

To reduce the size of the JSON, the graph entities are encoded as an
object with `value` and `is_uri` mapped to `v` and `e` respectively.

e.g.

Request:
```
{
    "vectors": [
      [
          0.04013510048389435,
          0.07536131888628006,
          ...
          -0.10790473222732544,
          0.03591292351484299
      ]
    ],
    "limit": 15
}
```

Response:

```
{
    "entities": [
        {
            "v": "http://trustgraph.ai/e/space-station-modules",
            "e": true
        },
        {
            "v": "http://trustgraph.ai/e/rocket-propellants",
            "e": true
        },
    ]
}
```

## Websocket

The websocket service accepts a request object containing the `vectors` field.
The response is a JSON object containing the `entities` field.

To reduce the size of the JSON, the graph entities are encoded as an
object with `value` and `is_uri` mapped to `v` and `e` respectively.

e.g.

Request:

```
{
    "id": "qgzw1287vfjc8wsk-3",
    "service": "graph-embeddings-query",
    "flow": "default",
    "request": {
        "vectors": [
          [
              0.04013510048389435,
              0.07536131888628006,
              ...
              -0.10790473222732544,
              0.03591292351484299
          ]
        ],
        "limit": 15
    }
}
```

Response:

```
{
    "id": "qgzw1287vfjc8wsk-3",
    "response": {
        "entities": [
            {
                "v": "http://trustgraph.ai/e/space-station-modules",
                "e": true
            },
            {
                "v": "http://trustgraph.ai/e/rocket-propellants",
                "e": true
            },
        ]
    },
    "complete": true
}
```

## Pulsar

The Pulsar schema for the Graph Embeddings API is defined in Python code here:

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/schema/graph.py

Default request queue:
`non-persistent://tg/request/graph-embeddings`

Default response queue:
`non-persistent://tg/response/graph-embeddings`

Request schema:
`trustgraph.schema.GraphEmbeddingsRequest`

Response schema:
`trustgraph.schema.GraphEmbeddingsResponse`

## Pulsar Python client

The client class is
`trustgraph.clients.GraphEmbeddingsClient`

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/clients/graph_embeddings.py








