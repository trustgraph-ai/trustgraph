from typing import Dict, Any, Tuple
from ...schema import (
    QuestionToSparqlRequest, QuestionToSparqlResponse, ResolvedEntity,
)
from .base import MessageTranslator


class QuestionToSparqlRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> QuestionToSparqlRequest:
        return QuestionToSparqlRequest(
            question=data.get("question", ""),
            collection=data.get("collection", ""),
            limit=int(data.get("limit", 10)),
        )

    def encode(self, obj: QuestionToSparqlRequest) -> Dict[str, Any]:
        return {
            "question": obj.question,
            "collection": obj.collection,
            "limit": obj.limit,
        }


class QuestionToSparqlResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> QuestionToSparqlResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: QuestionToSparqlResponse) -> Dict[str, Any]:
        result = {
            "sparql": obj.sparql,
            "resolved-entities": [
                {
                    "mention": e.mention,
                    "uri": e.uri,
                    "rdf-type": e.rdf_type,
                    "score": e.score,
                }
                for e in obj.resolved_entities
            ],
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        return result

    def encode_with_completion(
        self, obj: QuestionToSparqlResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
