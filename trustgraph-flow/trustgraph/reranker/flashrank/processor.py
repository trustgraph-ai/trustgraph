
"""
Reranker service using flashrank.
Scores query-document pairs and returns the top results ranked by
relevance.
"""

import asyncio
import logging

from ... base import RerankerService
from ... schema import RerankerResult

from flashrank import Ranker, RerankRequest

logger = logging.getLogger(__name__)

default_ident = "reranker"

default_model = "ms-marco-MiniLM-L-12-v2"

class Processor(RerankerService):

    def __init__(self, **params):

        model = params.get("model", default_model)

        super(Processor, self).__init__(
            **params | { "model": model }
        )

        self.default_model = model

        self.cached_model_name = None
        self.ranker = None

        self._load_model(model)

    def _load_model(self, model_name):
        if self.cached_model_name != model_name:
            logger.info(f"Loading flashrank model: {model_name}")
            self.ranker = Ranker(model_name=model_name)
            self.cached_model_name = model_name
            logger.info(f"flashrank model {model_name} loaded successfully")
        else:
            logger.debug(f"Using cached model: {model_name}")

    def _run_rerank(self, query, passages):
        request = RerankRequest(query=query, passages=passages)
        return self.ranker.rerank(request)

    async def on_rerank(self, queries, documents, limit, model=None):

        if not queries or not documents:
            return []

        use_model = model or self.default_model

        if self.cached_model_name != use_model:
            await asyncio.to_thread(self._load_model, use_model)

        passages = [
            {"id": d.document_id, "text": d.document_text}
            for d in documents
        ]

        best_scores = {}

        for q in queries:
            ranked = await asyncio.to_thread(
                self._run_rerank, q.query_text, passages,
            )

            for r in ranked:
                doc_id = r["id"]
                score = r["score"]
                score = float(score)
                if doc_id not in best_scores or score > best_scores[doc_id][1]:
                    best_scores[doc_id] = (q.query_id, score)

        results = sorted(
            best_scores.items(),
            key=lambda x: x[1][1],
            reverse=True,
        )[:limit]

        return [
            RerankerResult(
                document_id=doc_id,
                query_id=query_id,
                score=score,
            )
            for doc_id, (query_id, score) in results
        ]

    @staticmethod
    def add_args(parser):

        RerankerService.add_args(parser)

        parser.add_argument(
            '-m', '--model',
            default=default_model,
            help=f'Reranker model (default: {default_model})'
        )

def run():

    Processor.launch(default_ident, __doc__)
