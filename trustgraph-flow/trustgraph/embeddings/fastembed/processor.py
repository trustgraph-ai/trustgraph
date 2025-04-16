
"""
Embeddings service, applies an embeddings model selected from HuggingFace.
Input is text, output is embeddings vector.
"""

from ... schema import EmbeddingsRequest, EmbeddingsResponse
from ... base import RequestResponseService

from fastembed import TextEmbedding
import os

module = "embeddings"

default_subscriber = module
default_model="sentence-transformers/all-MiniLM-L6-v2"

class Processor(RequestResponseService):

    def __init__(self, **params):

        model = params.get("model", default_model)

        super(Processor, self).__init__(
            **params | {
                "model": model,
                "request_schema": EmbeddingsRequest,
                "response_schema": EmbeddingsResponse,
            }
        )

        self.embeddings = TextEmbedding(model_name = model)

    async def on_request(self, request, consumer, flow):

        text = request.text
        vecs = self.embeddings.embed([text])

        vecs = [
            v.tolist()
            for v in vecs
        ]

        return EmbeddingsResponse(
            vectors=list(vecs),
            error=None,
        )

    @staticmethod
    def add_args(parser):

        RequestResponseService.add_args(parser, default_subscriber)

        parser.add_argument(
            '-m', '--model',
            default=default_model,
            help=f'Embeddings model (default: {default_model})'
        )

def run():

    Processor.launch(module, __doc__)

