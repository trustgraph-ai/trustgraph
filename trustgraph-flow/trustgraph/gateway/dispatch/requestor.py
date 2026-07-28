
import asyncio
import logging
import time
from prometheus_client import Counter, Histogram

from ... base.request_response_client import RequestResponseClient

logger = logging.getLogger("requestor")
logger.setLevel(logging.INFO)

_gateway_metrics_initialized = False

def _init_gateway_metrics():
    global _gateway_metrics_initialized
    if _gateway_metrics_initialized:
        return
    _gateway_metrics_initialized = True

    from trustgraph.base.metrics import BUCKETS_SESSION
    ServiceRequestor.gateway_request_metric = Counter(
        'tg_gateway_request_total',
        'Gateway dispatched operations',
        ["service", "status"],
    )
    ServiceRequestor.gateway_request_duration_metric = Histogram(
        'tg_gateway_request_duration_seconds',
        'Gateway end-to-end request latency (seconds)',
        ["service"],
        buckets=BUCKETS_SESSION,
    )

class ServiceRequestor:

    def __init__(
            self,
            backend,
            request_queue, request_schema,
            response_queue, response_schema,
            subscription="api-gateway", consumer_name="api-gateway",
            timeout=600,
            service_kind=None,
    ):

        self.backend = backend
        self.request_queue = request_queue
        self.request_schema = request_schema
        self.response_queue = response_queue
        self.response_schema = response_schema
        self.timeout = timeout
        self.service_kind = service_kind
        self.client = None
        self.running = True

    async def start(self):
        self.running = True
        _init_gateway_metrics()
        self.client = await RequestResponseClient.create(
            backend=self.backend,
            request_topic=self.request_queue,
            response_topic=self.response_queue,
            request_schema=self.request_schema,
            response_schema=self.response_schema,
            processor_id="api-gateway",
            target_service=self.service_kind,
        )

    async def stop(self):
        self.running = False
        if self.client:
            await self.client.close()
            self.client = None

    def to_request(self, request):
        raise RuntimeError("Not defined")

    def from_response(self, response):
        raise RuntimeError("Not defined")

    async def process(self, request, responder=None):

        svc = self.service_kind or "unknown"
        t0 = time.monotonic()

        try:

            if responder is None:
                resp = await self.client.request(
                    self.to_request(request),
                    timeout=self.timeout,
                )

                if resp.error:
                    __class__.gateway_request_metric.labels(
                        service=svc, status="error",
                    ).inc()
                    __class__.gateway_request_duration_metric.labels(
                        service=svc,
                    ).observe(time.monotonic() - t0)
                    return { "error": {
                        "type": resp.error.type,
                        "message": resp.error.message,
                    } }

                result, fin = self.from_response(resp)
                __class__.gateway_request_metric.labels(
                    service=svc, status="ok",
                ).inc()
                __class__.gateway_request_duration_metric.labels(
                    service=svc,
                ).observe(time.monotonic() - t0)
                return result

            async for resp in self.client.request_stream(
                self.to_request(request),
                timeout=self.timeout,
            ):

                if resp.error:
                    err = { "error": {
                        "type": resp.error.type,
                        "message": resp.error.message,
                    } }
                    await responder(err, True)
                    __class__.gateway_request_metric.labels(
                        service=svc, status="error",
                    ).inc()
                    __class__.gateway_request_duration_metric.labels(
                        service=svc,
                    ).observe(time.monotonic() - t0)
                    return err

                result, fin = self.from_response(resp)
                await responder(result, fin)

                if fin:
                    __class__.gateway_request_metric.labels(
                        service=svc, status="ok",
                    ).inc()
                    __class__.gateway_request_duration_metric.labels(
                        service=svc,
                    ).observe(time.monotonic() - t0)
                    return result

        except Exception as e:

            logging.error(f"Exception: {e}")

            __class__.gateway_request_metric.labels(
                service=svc, status="error",
            ).inc()
            __class__.gateway_request_duration_metric.labels(
                service=svc,
            ).observe(time.monotonic() - t0)

            err = { "error": {
                "type": "gateway-error",
                "message": str(e),
            } }
            if responder:
                await responder(err, True)
            return err

