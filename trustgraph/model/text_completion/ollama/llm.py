
"""
Simple LLM service, performs text prompt completion using an Ollama service.
Input is prompt, output is response.
"""

from langchain_community.llms import Ollama
from prometheus_client import Histogram, Info, Counter

from .... schema import TextCompletionRequest, TextCompletionResponse
from .... schema import text_completion_request_queue
from .... schema import text_completion_response_queue
from .... log_level import LogLevel
from .... base import ConsumerProducer

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = text_completion_request_queue
default_output_queue = text_completion_response_queue
default_subscriber = module
default_model = 'gemma2'
default_ollama = 'http://localhost:11434'

class Processor(ConsumerProducer):

    def __init__(self, **params):

        input_queue = params.get("input_queue", default_input_queue)
        output_queue = params.get("output_queue", default_output_queue)
        subscriber = params.get("subscriber", default_subscriber)
        model = params.get("model", default_model)
        ollama = params.get("ollama", default_ollama)

        super(Processor, self).__init__(
            **params | {
                "input_queue": input_queue,
                "output_queue": output_queue,
                "subscriber": subscriber,
                "model": model,
                "ollama": ollama,
                "input_schema": TextCompletionRequest,
                "output_schema": TextCompletionResponse,
            }
        )

        if not hasattr(__class__, "model_metric"):
            __class__.model_metric = Info(
                'model', 'Model information'
            )

        __class__.model_metric.info({
            "model": model,
            "ollama": ollama,
        })

        self.llm = Ollama(base_url=ollama, model=model)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID
        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        prompt = v.prompt
        response = self.llm.invoke(prompt)

        print("Send response...", flush=True)

        r = TextCompletionResponse(response=response)

        self.send(r, properties={"id": id})

        print("Done.", flush=True)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-m', '--model',
            default="gemma2",
            help=f'LLM model (default: gemma2)'
        )

        parser.add_argument(
            '-r', '--ollama',
            default=default_ollama,
            help=f'ollama (default: {default_ollama})'
        )

def run():

    Processor.start(module, __doc__)

    
