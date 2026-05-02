
"""
Embeddings service, applies an embeddings model hosted on a local Ollama.
Input is text, output is embeddings vector.
"""
from ... base import EmbeddingsService

from ollama import AsyncClient
import os
import logging

logger = logging.getLogger(__name__)

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

        self.client = AsyncClient(host=ollama)
        self.default_model = model
        self._checked_models = set()

    async def _ensure_model(self, model_name):
        """Check if model exists locally, pull it if not."""
        if model_name in self._checked_models:
            return

        try:
            await self.client.show(model_name)
            self._checked_models.add(model_name)
        except Exception as e:
            status_code = getattr(e, 'status_code', None)
            if status_code == 404 or "not found" in str(e).lower():
                logger.info(f"Ollama model '{model_name}' not found locally. Pulling, this may take a while...")
                try:
                    await self.client.pull(model_name)
                    self._checked_models.add(model_name)
                    logger.info(f"Successfully pulled Ollama model '{model_name}'.")
                except Exception as pull_e:
                    logger.error(f"Failed to pull Ollama model '{model_name}': {pull_e}")
            else:
                logger.warning(f"Failed to check Ollama model '{model_name}': {e}")

    async def on_embeddings(self, texts, model=None):

        if not texts:
            return []

        use_model = model or self.default_model

        # Ensure the model exists/is pulled
        await self._ensure_model(use_model)

        # Ollama handles batch input efficiently
        embeds = await self.client.embed(
            model = use_model,
            input = texts
        )

        # Return list of vectors, one per input text
        return list(embeds.embeddings)

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


