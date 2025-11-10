
"""
Embeddings service, applies an embeddings model hosted on a local Ollama.
Input is text, output is embeddings vector.
"""
from ... base import EmbeddingsService

from ollama import Client
import os

default_ident = "embeddings"

default_model="mxbai-embed-large"
default_ollama = os.getenv("OLLAMA_HOST", 'http://localhost:11434')

class Processor(EmbeddingsService):

    def __init__(self, **params):

        model = params.get("model", default_model)
        ollama = params.get("ollama", default_ollama)

        super(Processor, self).__init__(
            **params | {
                "ollama": ollama,
                "model": model
            }
        )

        self.client = Client(host=ollama)
        self.default_model = model

    async def on_embeddings(self, text, model=None):

        use_model = model or self.default_model

        embeds = self.client.embed(
            model = use_model,
            input = text
        )

        return embeds.embeddings

    @staticmethod
    def add_args(parser):

        EmbeddingsService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default=default_model,
            help=f'Embeddings model (default: {default_model})'
        )

        parser.add_argument(
            '-r', '--ollama',
            default=default_ollama,
            help=f'ollama (default: {default_ollama})'
        )

def run():

    Processor.launch(default_ident, __doc__)


