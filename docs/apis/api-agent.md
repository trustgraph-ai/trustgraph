
# TrustGraph Agent API

The REST service provides incomplete functionality: The agent service
is able to provide multi-part responses containing 'thought' and
'observation' messages as the agent manager iterates over resolution of the
question.  These responses are provided in the websocket, but not the REST
API.

## Request

The request contains the following fields:
- `question`: A string, the question which the agent API must resolve
- `plan`: Optional, not used
- `state`: Optional, not used

## Response

The request contains the following fields:
- `thought`: Optional, a string, provides an interim agent thought
- `observation`: Optional, a string, provides an interim agent thought
- `answer`: Optional, a string, provides the final answer

## REST service

The REST service accepts a request object containing the question field.
The response is a JSON object containing the `answer` field.  Interim
responses are not provided.

e.g.

Request:
```
{
    "question": "What does NASA stand for?"
}
```

Response:

```
{
    "answer": "National Aeronautics and Space Administration"
}
```

## Websocket

Agent requests have a `request` object containing the `question` field.
Responses have a `response` object containing `thought`, `observation`
and `answer` fields in multi-part responses.  The final `answer` response
has `complete` set to `true`.

e.g.

Request:

```
{
    "id": "blrqotfefnmnh7de-20",
    "service": "agent",
    "request": {
        "question": "What does NASA stand for?"
    }
}
```

Responses:

```
{
    "id": "blrqotfefnmnh7de-20",
    "response": {
        "thought": "I need to query a knowledge base"
    },
    "complete": false
}
```

```
{
    "id": "blrqotfefnmnh7de-20",
    "response": {
        "observation": "National Aeronautics and Space Administration."
    },
    "complete": false
}
```

```
{
    "id": "blrqotfefnmnh7de-20",
    "response": {
        "thought": "I now know the final answer"
    },
    "complete": false
}
```

```
{
    "id": "blrqotfefnmnh7de-20",
    "response": {
        "answer": "National Aeronautics and Space Administration"
    },
    "complete": true
}
```

## Pulsar

The Pulsar schema for the Agent API is defined in Python code here:

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/schema/agent.py

Default request queue:
`non-persistent://tg/request/agent`

Default response queue:
`non-persistent://tg/response/agent`

Request schema:
`trustgraph.schema.AgentRequest`

Response schema:
`trustgraph.schema.AgentResponse`

## Pulsar Python client

The client class is
`trustgraph.clients.AgentClient`

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/clients/agent_client.py
