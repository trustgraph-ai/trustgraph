
"""
Embeddings service, applies an embeddings model using fastembed
Input is text, output is embeddings vector.
"""

from ... base import EmbeddingsService

from fastembed import TextEmbedding

default_ident = "embeddings"

default_model="sentence-transformers/all-MiniLM-L6-v2"

class Processor(EmbeddingsService):

    def __init__(self, **params):

        model = params.get("model", default_model)

        super(Processor, self).__init__(
            **params | { "model": model }
        )

        print("Get model...", flush=True)
        self.embeddings = TextEmbedding(model_name = model)

    async def on_embeddings(self, text):

        vecs = self.embeddings.embed([text])

        return [
            v.tolist()
            for v in vecs
        ]

    @staticmethod
    def add_args(parser):

        EmbeddingsService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default=default_model,
            help=f'Embeddings model (default: {default_model})'
        )

def run():

    Processor.launch(default_ident, __doc__)


