
from .. schema import EmbeddingsRequest, EmbeddingsResponse
from . base import BaseClient


# Ugly

class EmbeddingsClient(BaseClient):

    def __init__(
            self,
            input_queue=None,
            output_queue=None,
            subscriber=None,
            pulsar_host="pulsar://pulsar:6650",
            pulsar_api_key=None,
    ):

        super(EmbeddingsClient, self).__init__(
            subscriber=subscriber,
            input_queue=input_queue,
            output_queue=output_queue,
            pulsar_host=pulsar_host,
            pulsar_api_key=pulsar_api_key,
            input_schema=EmbeddingsRequest,
            output_schema=EmbeddingsResponse,
        )

    def request(self, text, timeout=300):
        return self.call(text=text, timeout=timeout).vectors

