from __future__ import annotations

import logging
from typing import Any

from . spec import Spec, TimeoutSpec

# Module logger
logger = logging.getLogger(__name__)


class ServiceNotConfiguredError(Exception):
    pass


class RequestResponseSpec(TimeoutSpec, Spec):

    default_timeout = 300

    def __init__(
            self, request_name, request_schema, response_name,
            response_schema, impl=None, optional=False, timeout=None,
    ):
        self.request_name = request_name
        self.request_schema = request_schema
        self.response_name = response_name
        self.response_schema = response_schema
        self.impl = impl
        self.optional = optional
        self.timeout = timeout

    async def register(self, flow: Any, processor: Any, definition: dict[str, Any]) -> Any:

        from .request_response_client import RequestResponseClient

        topics = definition.get("topics", {})

        if (
            self.request_name not in topics
            or self.response_name not in topics
        ):
            if self.optional is True:
                return None
            elif self.optional is Exception:
                wrapper = _make_error_wrapper(
                    self.request_name, self.impl,
                )
                flow.consumer[self.request_name] = wrapper
                return wrapper
            else:
                raise KeyError(self.request_name)

        rr_client = await RequestResponseClient.create(
            backend=processor.async_backend,
            request_topic=topics[self.request_name],
            response_topic=topics[self.response_name],
            request_schema=self.request_schema,
            response_schema=self.response_schema,
            processor_id=getattr(processor, 'id', None),
            target_service=self.request_name,
            default_timeout=self.resolve_timeout(processor),
        )

        wrapper = _make_impl_wrapper(rr_client, self.impl)
        flow.consumer[self.request_name] = wrapper
        return wrapper


def _make_impl_wrapper(rr_client, impl_cls):

    bases = (impl_cls,) if impl_cls is not None else ()

    class Wrapper(*bases):
        def __init__(self):
            self._rr_client = rr_client

        async def request(self, req, timeout=None, recipient=None):
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


def _make_error_wrapper(service_name, impl_cls):

    bases = (impl_cls,) if impl_cls is not None else ()

    class ErrorWrapper(*bases):
        def __init__(self):
            self._service_name = service_name

        def _raise(self):
            raise ServiceNotConfiguredError(
                f"Service '{self._service_name}' is not configured "
                f"in this flow"
            )

        async def request(self, req, timeout=None, recipient=None):
            self._raise()

        async def start(self):
            pass

        async def stop(self):
            pass

        async def close(self):
            pass

    return ErrorWrapper()

