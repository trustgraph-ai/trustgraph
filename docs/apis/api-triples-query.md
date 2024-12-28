
# TrustGraph Triples Query API

This is a service which queries the knowledge graph for triples ("facts").

## Request/response

### Request

The request contains the following fields:
- `s`: Optional, if included specifies a match for the subject part of a
  triple.
- `p`: Optional, if included specifies a match for the subject part of a
  triple.
- `o`: Optional, if included specifies a match for the subject part of a
  triple.
- `limit`: Optional, if included specifies the maximum number of triples to
  return.  If not specified, an arbitrary value is used.

Returned triples will match all of `s`, `p` and `o` where provided.

### Response

The request contains the following fields:
- `response`: A list of triples.

Each triple contains `s`, `p` and `o` fields describing the
subject, predicate and object part of each triple.

Each triple element uses the same schema:
- `value`: the entity URI or literal value depending on whether this is
  graph entity or literal value.
- `is_uri`: A boolean value which is true if this is a graph entity i.e.
  `value` is a URI, not a literal value.

## REST service

The REST service accepts a request object containing the `s`, `p`, `o`
and `limit` fields.
The response is a JSON object containing the `response` field.

To reduce the size of the JSON, the graph entities are encoded as an
object with `value` and `is_uri` mapped to `v` and `e` respectively.

e.g.

This example query matches triples with a subject of
`http://trustgraph.ai/e/space-station-modules` and a predicate of
`http://www.w3.org/2000/01/rdf-schema#label`.  This predicate
represents the RDF schema 'label' relationship.

The response is a single triple - the `o` element contains the
literal "space station modules" which is the label for
`http://trustgraph.ai/e/space-station-modules`.

Request:
```
{
    "id": "qgzw1287vfjc8wsk-4",
    "service": "triples-query",
    "request": {
        "s": {
            "v": "http://trustgraph.ai/e/space-station-modules",
            "e": true
        },
        "p": {
            "v": "http://www.w3.org/2000/01/rdf-schema#label",
            "e": true
        },
        "limit": 5
    }
}
```

Response:

```
{
    "response": [
        {
            "s": {
                "v": "http://trustgraph.ai/e/space-station-modules",
                "e": true
            },
            "p": {
                "v": "http://www.w3.org/2000/01/rdf-schema#label",
                "e": true
            },
            "o": {
                "v": "space station modules",
                "e": false
            }
        }
    ]
}
```

## Websocket

Requests have a `request` object containing the `system` and
`prompt` fields.
Responses have a `response` object containing `response` field.

To reduce the size of the JSON, the graph entities are encoded as an
object with `value` and `is_uri` mapped to `v` and `e` respectively.

e.g.

Request:

```
{
    "id": "qgzw1287vfjc8wsk-4",
    "service": "triples-query",
    "request": {
        "s": {
            "v": "http://trustgraph.ai/e/space-station-modules",
            "e": true
        },
        "p": {
            "v": "http://www.w3.org/2000/01/rdf-schema#label",
            "e": true
        },
        "limit": 5
    }
}
```

Responses:

```
{
    "id": "qgzw1287vfjc8wsk-4",
    "response": {
        "response": [
            {
                "s": {
                    "v": "http://trustgraph.ai/e/space-station-modules",
                    "e": true
                },
                "p": {
                    "v": "http://www.w3.org/2000/01/rdf-schema#label",
                    "e": true
                },
                "o": {
                    "v": "space station modules",
                    "e": false
                }
            }
        ]
    },
    "complete": true
}
```

## Pulsar

The Pulsar schema for the Triples Query API is defined in Python code here:

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/schema/graph.py

Default request queue:
`non-persistent://tg/request/triples-query`

Default response queue:
`non-persistent://tg/response/triples-query`

Request schema:
`trustgraph.schema.TriplesQueryRequest`

Response schema:
`trustgraph.schema.TriplesQueryResponse`

## Pulsar Python client

The client class is
`trustgraph.clients.TriplesQueryClient`

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/clients/triples_query_client.py








