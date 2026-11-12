from typing import Dict, Any, Tuple
from ...schema import (
    SparqlNLQueryRequest, SparqlNLQueryResponse, ResolvedEntity,
)
from .base import MessageTranslator


class SparqlNLQueryRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> SparqlNLQueryRequest:
        return SparqlNLQueryRequest(
            question=data.get("question", ""),
            collection=data.get("collection", ""),
            limit=int(data.get("limit", 10)),
        )

    def encode(self, obj: SparqlNLQueryRequest) -> Dict[str, Any]:
        return {
            "question": obj.question,
            "collection": obj.collection,
            "limit": obj.limit,
        }


class SparqlNLQueryResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> SparqlNLQueryResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: SparqlNLQueryResponse) -> Dict[str, Any]:
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
            "query-type": obj.query_type,
            "variables": obj.variables,
            "bindings": obj.bindings,
            "ask-result": obj.ask_result,
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        return result

    def encode_with_completion(
        self, obj: SparqlNLQueryResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
