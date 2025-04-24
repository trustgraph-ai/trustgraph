
from prometheus_client import start_http_server, Info, Enum, Histogram
from prometheus_client import Counter

class ConsumerMetrics:

    def __init__(self, processor, flow, name):

        self.processor = processor
        self.flow = flow
        self.name = name

        if not hasattr(__class__, "state_metric"):
            __class__.state_metric = Enum(
                'consumer_state', 'Consumer state',
                ["processor", "flow", "name"],
                states=['stopped', 'running']
            )

        if not hasattr(__class__, "request_metric"):
            __class__.request_metric = Histogram(
                'request_latency', 'Request latency (seconds)',
                ["processor", "flow", "name"],
            )

        if not hasattr(__class__, "processing_metric"):
            __class__.processing_metric = Counter(
                'processing_count', 'Processing count',
                ["processor", "flow", "name", "status"],
            )

        if not hasattr(__class__, "rate_limit_metric"):
            __class__.rate_limit_metric = Counter(
                'rate_limit_count', 'Rate limit event count',
                ["processor", "flow", "name"],
            )

    def process(self, status):
        __class__.processing_metric.labels(
            processor = self.processor, flow = self.flow, name = self.name,
            status=status
        ).inc()

    def rate_limit(self):
        __class__.rate_limit_metric.labels(
            processor = self.processor, flow = self.flow, name = self.name,
        ).inc()

    def state(self, state):
        __class__.state_metric.labels(
            processor = self.processor, flow = self.flow, name = self.name,
        ).state(state)

    def record_time(self):
        return __class__.request_metric.labels(
            processor = self.processor, flow = self.flow, name = self.name,
        ).time()

class ProducerMetrics:

    def __init__(self, processor, flow, name):

        self.processor = processor
        self.flow = flow
        self.name = name

        if not hasattr(__class__, "producer_metric"):
            __class__.producer_metric = Counter(
                'producer_count', 'Output items produced',
                ["processor", "flow", "name"],
            )

    def inc(self):
        __class__.producer_metric.labels(
            processor = self.processor, flow = self.flow, name = self.name
        ).inc()

class ProcessorMetrics:
    def __init__(self, processor):

        self.processor = processor

        if not hasattr(__class__, "processor_metric"):
            __class__.processor_metric = Info(
                'processor', 'Processor configuration',
                ["processor"]
            )

    def info(self, info):
        __class__.processor_metric.labels(
            processor = self.processor
        ).info(info)

class SubscriberMetrics:

    def __init__(self, processor, flow, name):

        self.processor = processor
        self.flow = flow
        self.name = name

        if not hasattr(__class__, "state_metric"):
            __class__.state_metric = Enum(
                'subscriber_state', 'Subscriber state',
                ["processor", "flow", "name"],
                states=['stopped', 'running']
            )

        if not hasattr(__class__, "received_metric"):
            __class__.received_metric = Counter(
                'received_count', 'Received count',
                ["processor", "flow", "name"],
            )

        if not hasattr(__class__, "dropped_metric"):
            __class__.dropped_metric = Counter(
                'dropped_count', 'Dropped messages count',
                ["processor", "flow", "name"],
            )

    def received(self):
        __class__.received_metric.labels(
            processor = self.processor, flow = self.flow, name = self.name,
        ).inc()

    def state(self, state):

        __class__.state_metric.labels(
            processor = self.processor, flow = self.flow, name = self.name,
        ).state(state)

    def dropped(self, state):
        __class__.dropped_metric.labels(
            processor = self.processor, flow = self.flow, name = self.name,
        ).inc()

