from __future__ import annotations

import logging
from typing import Any

from . spec import Spec

# Module logger
logger = logging.getLogger(__name__)

# This deals with the request/response case.  The caller needs to
# use another service in request/response mode.  Uses two topics:
# - we send on the request topic as a producer
# - we receive on the response topic as a subscriber
class RequestResponseSpec(Spec):
    def __init__(
            self, request_name, request_schema, response_name,
            response_schema, impl=None, optional=False
    ):
        self.request_name = request_name
        self.request_schema = request_schema
        self.response_name = response_name
        self.response_schema = response_schema
        self.impl = impl
        self.optional = optional

    async def register(self, flow: Any, processor: Any, definition: dict[str, Any]) -> Any:

        from .request_response_client import RequestResponseClient

        topics = definition.get("topics", {})
        if self.optional and (
                self.request_name not in topics
                or self.response_name not in topics):
            return None

        rr_client = await RequestResponseClient.create(
            backend=processor.async_backend,
            request_topic=topics[self.request_name],
            response_topic=topics[self.response_name],
            request_schema=self.request_schema,
            response_schema=self.response_schema,
            processor_id=getattr(processor, 'id', None),
            target_service=self.request_name,
        )

        wrapper = _make_impl_wrapper(rr_client, self.impl)
        flow.consumer[self.request_name] = wrapper
        return wrapper


def _make_impl_wrapper(rr_client, impl_cls):
    """Create a domain-specific wrapper that delegates request() to the
    RequestResponseClient while inheriting business methods from impl_cls."""

    bases = (impl_cls,) if impl_cls is not None else ()

    class Wrapper(*bases):
        def __init__(self):
            self._rr_client = rr_client

        async def request(self, req, timeout=300, recipient=None):
            if recipient is None:
                return await self._rr_client.request(req, timeout=timeout)

            async for resp in self._rr_client.request_stream(req, timeout=timeout):
                fin = await recipient(resp)
                if fin:
                    return resp

        async def start(self):
            pass

        async def stop(self):
            await self._rr_client.close()

        async def close(self):
            await self._rr_client.close()

    return Wrapper()

