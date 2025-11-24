
"""
Embeddings service, applies an embeddings model using fastembed
Input is text, output is embeddings vector.
"""

import logging

from ... base import EmbeddingsService

from fastembed import TextEmbedding

# Module logger
logger = logging.getLogger(__name__)

default_ident = "embeddings"

default_model="sentence-transformers/all-MiniLM-L6-v2"

class Processor(EmbeddingsService):

    def __init__(self, **params):

        model = params.get("model", default_model)

        super(Processor, self).__init__(
            **params | { "model": model }
        )

        self.default_model = model

        # Cache for currently loaded model
        self.cached_model_name = None
        self.embeddings = None

        # Load the default model
        self._load_model(model)

    def _load_model(self, model_name):
        """Load a model, caching it for reuse"""
        if self.cached_model_name != model_name:
            logger.info(f"Loading FastEmbed model: {model_name}")
            self.embeddings = TextEmbedding(model_name=model_name)
            self.cached_model_name = model_name
            logger.info(f"FastEmbed model {model_name} loaded successfully")
        else:
            logger.debug(f"Using cached model: {model_name}")

    async def on_embeddings(self, text, model=None):

        use_model = model or self.default_model

        # Reload model if it has changed
        self._load_model(use_model)

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

