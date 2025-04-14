
from prometheus_client import start_http_server, Info, Enum, Histogram
from prometheus_client import Counter

class ConsumerMetrics:

    def __init__(self, id, flow=None):

        self.id = id
        self.flow = flow

        if not hasattr(__class__, "state_metric"):
            __class__.state_metric = Enum(
                'consumer_state', 'Consumer state',
                ["id", "flow"],
                states=['stopped', 'running']
            )
        if not hasattr(__class__, "request_metric"):
            __class__.request_metric = Histogram(
                'request_latency', 'Request latency (seconds)',
                ["id", "flow"],
            )
        if not hasattr(__class__, "processing_metric"):
            __class__.processing_metric = Counter(
                'processing_count', 'Processing count',
                ["id", "flow", "status"]
            )
        if not hasattr(__class__, "rate_limit_metric"):
            __class__.rate_limit_metric = Counter(
                'rate_limit_count', 'Rate limit event count',
                ["id", "flow"]
            )

    def process(self, status):
        __class__.processing_metric.labels(
            id=self.id, flow=self.flow, status=status
        ).inc()

    def rate_limit(self):
        __class__.rate_limit_metric.labels(
            id=self.id, flow=self.flow
        ).inc()

    def state(self, state):
        __class__.state_metric.labels(
            id=self.id, flow=self.flow
        ).state(state)

    def record_time(self):
        return __class__.request_metric.labels(
            id=self.id, flow=self.flow
        ).time()

class ProducerMetrics:
    def __init__(self, id, flow=None):

        self.id = id
        self.flow = flow

        if not hasattr(__class__, "output_metric"):
            __class__.output_metric = Counter(
                'output_count', 'Output items created',
                ["id", "flow"]
            )

    def inc(self):
        __class__.output_metric.labels(id=self.id, flow=self.flow).inc()

class ProcessorMetrics:
    def __init__(self, id):

        self.id = id

        if not hasattr(__class__, "pubsub_metric"):
            __class__.pubsub_metric = Info(
                'pubsub', 'Pub/sub configuration',
                ["id"]
            )

    def info(self, info):
        __class__.pubsub_metric.labels(id=self.id).info(info)
        
