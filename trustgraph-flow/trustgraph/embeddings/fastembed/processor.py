
"""
Embeddings service, applies an embeddings model using fastembed
Input is text, output is embeddings vector.
"""

import asyncio
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
        """Load a model, caching it for reuse.

        Synchronous — CPU and I/O heavy.  Callers that run on the
        event loop must dispatch via asyncio.to_thread to avoid
        freezing the loop (which, in processor-group deployments,
        freezes every sibling processor in the same process).
        """
        if self.cached_model_name != model_name:
            logger.info(f"Loading FastEmbed model: {model_name}")
            self.embeddings = TextEmbedding(model_name=model_name)
            self.cached_model_name = model_name
            logger.info(f"FastEmbed model {model_name} loaded successfully")
        else:
            logger.debug(f"Using cached model: {model_name}")

    def _run_embed(self, texts):
        """Synchronous embed call.  Runs in a worker thread via
        asyncio.to_thread from on_embeddings."""
        return list(self.embeddings.embed(texts))

    async def on_embeddings(self, texts, model=None):

        if not texts:
            return []

        use_model = model or self.default_model

        # Reload model if it has changed.  Model loading is sync
        # and can take seconds; push it to a worker thread so the
        # event loop (and any sibling processors in group mode)
        # stay responsive.
        if self.cached_model_name != use_model:
            await asyncio.to_thread(self._load_model, use_model)

        # FastEmbed inference is synchronous ONNX runtime work.
        # Dispatch to a worker thread so the event loop stays
        # responsive for other tasks (important in group mode
        # where the loop is shared across many processors).
        vecs = await asyncio.to_thread(self._run_embed, texts)

        # Return list of vectors, one per input text
        return [v.tolist() for v in vecs]

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

