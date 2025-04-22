
"""
Embeddings service, applies an embeddings model selected from HuggingFace.
Input is text, output is embeddings vector.
"""

from ... base import EmbeddingsService

from langchain_huggingface import HuggingFaceEmbeddings

default_ident = "embeddings"

default_model="all-MiniLM-L6-v2"

class Processor(EmbeddingsService):

    def __init__(self, **params):

        model = params.get("model", default_model)

        super(Processor, self).__init__(
            **params | { "model": model }
        )

        print("Get model...", flush=True)
        self.embeddings = HuggingFaceEmbeddings(model_name=model)

    async def on_embeddings(self, text):

        embeds = self.embeddings.embed_documents([text])
        print("Done.", flush=True)
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

