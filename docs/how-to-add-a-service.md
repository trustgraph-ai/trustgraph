---
layout: default
title: "How to Add a Request/Response Service"
parent: "Tech Specs"
---

# How to Add a Request/Response Service

Checklist for wiring a new request/response service through the full
TrustGraph stack. The examples use a hypothetical service called
`my-service` with request/response types `MyServiceRequest` and
`MyServiceResponse`.

Streaming services (multi-part responses) follow the same steps with
minor additions noted inline.

## 1. Schema (trustgraph-base)

**File**: `trustgraph/schema/my_service.py`

Define the request and response dataclasses, plus queue definitions.

```python
from dataclasses import dataclass
from .core.primitives import Error
from .core.topic import queue

@dataclass
class MyServiceRequest:
    query: str = ""

@dataclass
class MyServiceResponse:
    result: str = ""
    error: Error | None = None
    # Streaming only:
    end_of_stream: bool = False

my_service_request_queue = queue('my-service', cls='request')
my_service_response_queue = queue('my-service', cls='response')
```

**File**: `trustgraph/schema/__init__.py` -- add the wildcard import:

```python
from .my_service import *
```

## 2. Base client (trustgraph-base)

**File**: `trustgraph/base/my_service_client.py`

```python
from . request_response_spec import RequestResponseSpec
from .. schema import MyServiceRequest, MyServiceResponse

class MyServiceClient:
    async def do_something(self, query, timeout=120):
        resp = await self.request(
            MyServiceRequest(query=query),
            timeout=timeout,
        )
        if resp.error:
            raise RuntimeError(resp.error.message)
        return resp.result

class MyServiceClientSpec(RequestResponseSpec):
    def __init__(self, request_name, response_name):
        super().__init__(
            request_name=request_name,
            request_schema=MyServiceRequest,
            response_name=response_name,
            response_schema=MyServiceResponse,
            impl=MyServiceClient,
        )
```

For streaming services, the client uses a `recipient` callback pattern
to accumulate multi-part responses. See `DocumentDecoderClient` for an
example.

**File**: `trustgraph/base/__init__.py` -- add the export:

```python
from . my_service_client import MyServiceClientSpec
```

## 3. Translator (trustgraph-base)

**File**: `trustgraph/messaging/translators/my_service.py`

Translates between JSON wire format (gateway/SDK) and schema
dataclasses (Pulsar).

```python
from typing import Dict, Any, Tuple
from ...schema import MyServiceRequest, MyServiceResponse
from .base import MessageTranslator

class MyServiceRequestTranslator(MessageTranslator):
    def decode(self, data: Dict[str, Any]) -> MyServiceRequest:
        return MyServiceRequest(query=data.get("query", ""))

    def encode(self, obj: MyServiceRequest) -> Dict[str, Any]:
        return {"query": obj.query}

class MyServiceResponseTranslator(MessageTranslator):
    def decode(self, data: Dict[str, Any]) -> MyServiceResponse:
        raise NotImplementedError

    def encode(self, obj: MyServiceResponse) -> Dict[str, Any]:
        result = {"result": obj.result}
        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }
        return result

    def encode_with_completion(
        self, obj: MyServiceResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
```

For streaming services, `encode_with_completion` must return
`is_final` based on `end_of_stream`:

```python
    def encode_with_completion(self, obj):
        is_final = getattr(obj, 'end_of_stream', True)
        return self.encode(obj), is_final
```

## 4. Translator registration (trustgraph-base)

**File**: `trustgraph/messaging/translators/__init__.py` -- add import:

```python
from .my_service import MyServiceRequestTranslator, MyServiceResponseTranslator
```

**File**: `trustgraph/messaging/__init__.py` -- add import and
registration:

```python
from .translators.my_service import MyServiceRequestTranslator, MyServiceResponseTranslator

TranslatorRegistry.register_service(
    "my-service",
    MyServiceRequestTranslator(),
    MyServiceResponseTranslator()
)
```

The string `"my-service"` is the translator key used by the gateway
dispatcher. It must match the key used in the dispatcher's
`TranslatorRegistry.get_request_translator(...)` call.

## 5. Gateway dispatcher (trustgraph-flow)

**File**: `trustgraph/gateway/dispatch/my_service.py`

```python
from ... schema import MyServiceRequest, MyServiceResponse
from ... messaging import TranslatorRegistry
from . requestor import ServiceRequestor

class MyServiceRequestor(ServiceRequestor):
    def __init__(self, backend, request_queue, response_queue,
                 timeout, consumer, subscriber):
        super().__init__(
            backend=backend,
            request_queue=request_queue,
            response_queue=response_queue,
            request_schema=MyServiceRequest,
            response_schema=MyServiceResponse,
            subscription=subscriber,
            consumer_name=consumer,
            timeout=timeout,
        )
        self.request_translator = TranslatorRegistry.get_request_translator("my-service")
        self.response_translator = TranslatorRegistry.get_response_translator("my-service")

    def to_request(self, body):
        return self.request_translator.decode(body)

    def from_response(self, message):
        return self.response_translator.encode_with_completion(message)
```

## 6. Gateway manager (trustgraph-flow)

**File**: `trustgraph/gateway/dispatch/manager.py`

Add import:

```python
from . my_service import MyServiceRequestor
```

Add to `request_response_dispatchers`:

```python
request_response_dispatchers = {
    ...
    "my-service": MyServiceRequestor,
}
```

The key `"my-service"` is the service name used in WebSocket frames
(`"service": "my-service"`) and in the gateway's interface lookup.

## 7. Gateway registry (trustgraph-flow)

**File**: `trustgraph/gateway/registry.py`

Add to the `_FLOW_SERVICES` dict:

```python
_FLOW_SERVICES = {
    ...
    "my-service": "my-service",
}
```

The value is the IAM capability string. Use `"my-service:read"` /
`"my-service:write"` if you need read/write separation.

## 8. IAM capabilities

The capability string from step 7 must be granted to users.

**Open source** -- `trustgraph-flow/trustgraph/iam/service/iam.py`:
add to `_READER_CAPS` (or `_WRITER_CAPS` for write operations).

Forgetting this step causes "access denied" errors with no other
indication of what's wrong.

Note to Enterprise maintainers: The same capability needs to be
registered in Enterprise.  Add to `ADMIN_CAPABILITIES`.

## 9. Processor (service implementation)

The processor registers `ConsumerSpec` and `ProducerSpec` for the
request/response queues. The spec names **must** be `"request"` and
`"response"` to match the flow blueprint convention.

```python
self.register_specification(
    ConsumerSpec(
        name="request",
        schema=MyServiceRequest,
        handler=self.on_request,
    )
)

self.register_specification(
    ProducerSpec(
        name="response",
        schema=MyServiceResponse,
    )
)
```

The handler extracts the correlation ID and sends responses with it:

```python
async def on_request(self, msg, consumer, flow):
    id = msg.properties()["id"]
    try:
        v = msg.value()
        # ... process ...
        await flow("response").send(
            MyServiceResponse(result=result),
            properties={"id": id},
        )
    except Exception as e:
        await flow("response").send(
            MyServiceResponse(
                error=Error(type="my-service-error", message=str(e)),
            ),
            properties={"id": id},
        )
```

For streaming services, send multiple responses with
`end_of_stream=False`, then a final message with
`end_of_stream=True`.

## 10. Flow blueprint

The processor's flow definition must include topic entries for
`request` and `response` matching the spec names from step 9:

```json
{
  "topics": {
    "request": "request:tg:my-service:default:default",
    "response": "response:tg:my-service:default:default"
  }
}
```

The gateway also needs a matching interface entry so it can route
WebSocket requests to the correct queues:

```json
{
  "interfaces": {
    "my-service": {
      "request": "request:tg:my-service:default:default",
      "response": "response:tg:my-service:default:default"
    }
  }
}
```

The interface key must match the dispatcher key from step 6.

## 11. SDK (trustgraph-base)

**File**: `trustgraph/api/socket_client.py` -- add method to
`SocketFlowInstance`:

```python
def my_service(self, query, **kwargs):
    request = {"query": query}
    request.update(kwargs)
    return self.client._send_request_sync(
        "my-service", self.flow_id, request, False
    )
```

**File**: `trustgraph/api/async_socket_client.py` -- add async
equivalent to `AsyncSocketFlowInstance`:

```python
async def my_service(self, query, **kwargs):
    request = {"query": query}
    request.update(kwargs)
    return await self.client._send_request(
        "my-service", self.flow_id, request
    )
```

For streaming services, use `streaming_raw=True` (sync) or
`_send_request_streaming_raw` (async) and accumulate responses until
`end_of_stream` is `True`.

## 12. CLI (trustgraph-cli)

**File**: `trustgraph/cli/invoke_my_service.py`

Standard CLI pattern: parse args, create `Api`, open socket, call SDK
method, print result. See `invoke_cloze.py` for a minimal example.

**File**: `pyproject.toml` -- register the entry point:

```toml
[project.scripts]
tg-invoke-my-service = "trustgraph.cli.invoke_my_service:main"
```

## Common mistakes

- **Spec names**: Using anything other than `"request"` and
  `"response"` for the processor's ConsumerSpec/ProducerSpec names.
  The flow blueprint maps these by name.

- **Missing IAM capability**: The service works in development but
  returns "access denied" in any IAM-enabled deployment. Must be
  added to both open-source and enterprise IAM.

- **Translator key mismatch**: The string passed to
  `TranslatorRegistry.register_service()` must match the string used
  in `TranslatorRegistry.get_request_translator()` in the dispatcher.

- **Missing flow blueprint entries**: The processor subscribes based
  on the `topics` dict in its flow definition. If `"request"` is
  missing, the processor starts but never receives messages -- it
  hangs silently.

- **Streaming completion**: For streaming services, if
  `encode_with_completion` always returns `True`, the gateway closes
  the stream after the first response frame. It must return `False`
  for intermediate frames and `True` only on the final frame.

- **Correlation ID**: Every response must include
  `properties={"id": id}` where `id` comes from
  `msg.properties()["id"]`. Without this, the gateway can't match
  responses to requests.
