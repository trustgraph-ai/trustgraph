
"""
Simple LLM service, performs text prompt completion using an Ollama service.
Input is prompt, output is response.
"""

from ollama import Client
from prometheus_client import Histogram, Info
import os

from .... schema import TextCompletionRequest, TextCompletionResponse, Error
from .... schema import text_completion_request_queue
from .... schema import text_completion_response_queue
from .... log_level import LogLevel
from .... base import ConsumerProducer
from .... exceptions import TooManyRequests

module = ".".join(__name__.split(".")[1:-1])

default_input_queue = text_completion_request_queue
default_output_queue = text_completion_response_queue
default_subscriber = module
default_model = 'gemma2:9b'
default_ollama = os.getenv("OLLAMA_HOST", 'http://localhost:11434')

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

        if not hasattr(__class__, "text_completion_metric"):
            __class__.text_completion_metric = Histogram(
                'text_completion_duration',
                'Text completion duration (seconds)',
                buckets=[
                    0.25, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0,
                    8.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0,
                    17.0, 18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0,
                    30.0, 35.0, 40.0, 45.0, 50.0, 60.0, 80.0, 100.0,
                    120.0
                ]
            )

        if not hasattr(__class__, "model_metric"):
            __class__.model_metric = Info(
                'model', 'Model information'
            )

        __class__.model_metric.info({
            "model": model,
            "ollama": ollama,
        })

        self.model = model
        self.llm = Client(host=ollama)

    def handle(self, msg):

        v = msg.value()

        # Sender-produced ID
        id = msg.properties()["id"]

        print(f"Handling prompt {id}...", flush=True)

        prompt = v.system + "\n\n" + v.prompt

        try:

            with __class__.text_completion_metric.time():
                response = self.llm.generate(self.model, prompt)

            response_text = response['response']
            print("Send response...", flush=True)
            print(response_text, flush=True)

            inputtokens = int(response['prompt_eval_count'])
            outputtokens = int(response['eval_count'])

            r = TextCompletionResponse(response=response_text, error=None, in_token=inputtokens, out_token=outputtokens, model="ollama")

            self.send(r, properties={"id": id})

            print("Done.", flush=True)

        # FIXME: Wrong exception, don't know what this LLM throws
        # for a rate limit
        except TooManyRequests:

            print("Send rate limit response...", flush=True)

            r = TextCompletionResponse(
                error=Error(
                    type = "rate-limit",
                    message = str(e),
                ),
                response=None,
                in_token=None,
                out_token=None,
                model=None,
            )

            self.producer.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = TextCompletionResponse(
                error=Error(
                    type = "llm-error",
                    message = str(e),
                ),
                response=None,
                in_token=None,
                out_token=None,
                model=None,
            )

            self.producer.send(r, properties={"id": id})

            self.consumer.acknowledge(msg)

    @staticmethod
    def add_args(parser):

        ConsumerProducer.add_args(
            parser, default_input_queue, default_subscriber,
            default_output_queue,
        )

        parser.add_argument(
            '-m', '--model',
            default="gemma2",
            help=f'LLM model (default: {default_model})'
        )

        parser.add_argument(
            '-r', '--ollama',
            default=default_ollama,
            help=f'ollama (default: {default_ollama})'
        )

def run():

    Processor.start(module, __doc__)

    
