
"""
Embeddings service, applies an embeddings model selected from HuggingFace.
Input is text, output is embeddings vector.
"""

import logging
from ... base import EmbeddingsService

from langchain_huggingface import HuggingFaceEmbeddings

# Module logger
logger = logging.getLogger(__name__)

default_ident = "embeddings"

default_model="all-MiniLM-L6-v2"

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
            logger.info(f"Loading HuggingFace embeddings model: {model_name}")
            self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
            self.cached_model_name = model_name
            logger.info(f"HuggingFace model {model_name} loaded successfully")
        else:
            logger.debug(f"Using cached model: {model_name}")

    async def on_embeddings(self, text, model=None):

        use_model = model or self.default_model

        # Reload model if it has changed
        self._load_model(use_model)

        embeds = self.embeddings.embed_documents([text])
        logger.debug("Embeddings generation complete")
        return embeds

    @staticmethod
    def add_args(parser):

        EmbeddingsService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default="all-MiniLM-L6-v2",
            help=f'LLM model (default: all-MiniLM-L6-v2)'
        )

def run():

    Processor.launch(default_ident, __doc__)

