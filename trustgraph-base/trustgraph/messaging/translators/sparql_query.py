from typing import Dict, Any, Tuple
from ...schema import (
    SparqlQueryRequest, SparqlQueryResponse, SparqlBinding,
    Error, Term, Triple, IRI, LITERAL, BLANK,
)
from .base import MessageTranslator
from .primitives import TermTranslator, TripleTranslator


class SparqlQueryRequestTranslator(MessageTranslator):
    """Translator for SparqlQueryRequest schema objects."""

    def decode(self, data: Dict[str, Any]) -> SparqlQueryRequest:
        return SparqlQueryRequest(
            user=data.get("user", "trustgraph"),
            collection=data.get("collection", "default"),
            query=data.get("query", ""),
            limit=int(data.get("limit", 10000)),
        )

    def encode(self, obj: SparqlQueryRequest) -> Dict[str, Any]:
        return {
            "user": obj.user,
            "collection": obj.collection,
            "query": obj.query,
            "limit": obj.limit,
        }


class SparqlQueryResponseTranslator(MessageTranslator):
    """Translator for SparqlQueryResponse schema objects."""

    def __init__(self):
        self.term_translator = TermTranslator()
        self.triple_translator = TripleTranslator()

    def decode(self, data: Dict[str, Any]) -> SparqlQueryResponse:
        raise NotImplementedError(
            "Response translation to schema not typically needed"
        )

    def _encode_term(self, v):
        """Encode a Term, handling both Term objects and dicts from
        pub/sub deserialization."""
        if v is None:
            return None
        if isinstance(v, dict):
            # Reconstruct Term from dict (pub/sub deserializes nested
            # dataclasses as dicts)
            term = Term(
                type=v.get("type", ""),
                iri=v.get("iri", ""),
                id=v.get("id", ""),
                value=v.get("value", ""),
                datatype=v.get("datatype", ""),
                language=v.get("language", ""),
            )
            return self.term_translator.encode(term)
        return self.term_translator.encode(v)

    def _encode_error(self, error):
        """Encode an Error, handling both Error objects and dicts."""
        if isinstance(error, dict):
            return {
                "type": error.get("type", ""),
                "message": error.get("message", ""),
            }
        return {
            "type": error.type,
            "message": error.message,
        }

    def encode(self, obj: SparqlQueryResponse) -> Dict[str, Any]:
        result = {
            "query-type": obj.query_type,
        }

        if obj.error:
            result["error"] = self._encode_error(obj.error)

        if obj.query_type == "select":
            result["variables"] = obj.variables
            bindings = []
            for binding in obj.bindings:
                # binding may be a SparqlBinding or a dict
                if isinstance(binding, dict):
                    values = binding.get("values", [])
                else:
                    values = binding.values
                bindings.append({
                    "values": [
                        self._encode_term(v) for v in values
                    ]
                })
            result["bindings"] = bindings

        elif obj.query_type == "ask":
            result["ask-result"] = obj.ask_result

        elif obj.query_type in ("construct", "describe"):
            result["triples"] = [
                self.triple_translator.encode(t)
                for t in obj.triples
            ]

        return result

    def encode_with_completion(
        self, obj: SparqlQueryResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
