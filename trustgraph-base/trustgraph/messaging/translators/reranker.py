from typing import Dict, Any, Tuple
from ...schema import (
    RerankerRequest, RerankerResponse,
    RerankerQuery, RerankerDocument, RerankerResult,
)
from .base import MessageTranslator


class RerankerRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> RerankerRequest:
        return RerankerRequest(
            queries=[
                RerankerQuery(
                    query_id=q["query_id"],
                    query_text=q["query_text"],
                )
                for q in data.get("queries", [])
            ],
            documents=[
                RerankerDocument(
                    document_id=d["document_id"],
                    document_text=d["document_text"],
                )
                for d in data.get("documents", [])
            ],
            limit=data.get("limit", 10),
        )

    def encode(self, obj: RerankerRequest) -> Dict[str, Any]:
        return {
            "queries": [
                {"query_id": q.query_id, "query_text": q.query_text}
                for q in obj.queries
            ],
            "documents": [
                {"document_id": d.document_id, "document_text": d.document_text}
                for d in obj.documents
            ],
            "limit": obj.limit,
        }


class RerankerResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> RerankerResponse:
        return RerankerResponse(
            results=[
                RerankerResult(
                    document_id=r["document_id"],
                    query_id=r["query_id"],
                    score=r["score"],
                )
                for r in data.get("results", [])
            ],
        )

    def encode(self, obj: RerankerResponse) -> Dict[str, Any]:
        return {
            "results": [
                {
                    "document_id": r.document_id,
                    "query_id": r.query_id,
                    "score": r.score,
                }
                for r in obj.results
            ],
        }

    def encode_with_completion(
        self, obj: RerankerResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
