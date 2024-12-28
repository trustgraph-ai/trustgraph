
# TrustGraph websocket overview

The websocket service is provided by the `api-gateway` service on port
8088.

## URL

Depending on how the service is hosted, the websocket is invoked on this
URL on `api-gateway`:

```
/api/v1/socket
```

When hosted using docker compose, you can access the service at
`ws://localhost:8088/api/v1/socket`

## Request

A request message is a JSON message containing 3 fields:

- `id`: A unique ID which is used to correlate requests and responses.
  You should make sure it is unique.
- `service`: The name of the service to invoke.
- `request`: The request body which is passed to the service - this is
  defined in the API documentation for that service.

e.g.

```
{
    "id": "qgzw1287vfjc8wsk-1",
    "service": "graph-rag",
    "request": {
        "query": "What does NASA stand for?"
    }
}
```

## Response

A response message is JSON encoded, and may contain the following fields:

- `id`: This is the same value provided on the request and shows which
  request this response is returned for.
- `error`: If an error occured, this field is provided, and provides an
  error message.
- `response`: For a non-error case, this provides a response from the
  service - the response structure depends on the service invoked.  It is
  not provided if the `error` field is provided.
- `complete`: A boolean value indicating whether this response is the
  final response from the service.  If set to false, the response values
  are intermediate values.   It is not provided if the `error` field is
  provided.
  
An error response completes a request - no further responses
will be provided.

e.g.

```
{
    "id": "qgzw1287vfjc8wsk-1",
    "response": {
        "response": "National Aeronautics and Space Administration."
    },
    "complete": true
}
```

