from typing import Dict, Any, Tuple
from ...schema import (
    KnowledgeRetrievalRequest, KnowledgeRetrievalResponse, RetrievedEdge,
)
from .base import MessageTranslator


class KnowledgeRetrievalRequestTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> KnowledgeRetrievalRequest:
        return KnowledgeRetrievalRequest(
            concepts=data.get("concepts", []),
            entities=data.get("entities", []),
            entity_limit=data.get("entity-limit", 50),
            triple_limit=data.get("triple-limit", 30),
            max_path_length=data.get("max-path-length", 2),
            edge_limit=data.get("edge-limit", 25),
            max_reranker_input=data.get("max-reranker-input", 350),
            languages=data.get("languages", []),
            graph=data.get("graph", ""),
        )

    def encode(self, obj: KnowledgeRetrievalRequest) -> Dict[str, Any]:
        result = {}
        if obj.concepts:
            result["concepts"] = list(obj.concepts)
        if obj.entities:
            result["entities"] = list(obj.entities)
        if obj.entity_limit != 50:
            result["entity-limit"] = obj.entity_limit
        if obj.triple_limit != 30:
            result["triple-limit"] = obj.triple_limit
        if obj.max_path_length != 2:
            result["max-path-length"] = obj.max_path_length
        if obj.edge_limit != 25:
            result["edge-limit"] = obj.edge_limit
        if obj.max_reranker_input != 350:
            result["max-reranker-input"] = obj.max_reranker_input
        if obj.languages:
            result["languages"] = list(obj.languages)
        if obj.graph:
            result["graph"] = obj.graph
        return result


class KnowledgeRetrievalResponseTranslator(MessageTranslator):

    def decode(self, data: Dict[str, Any]) -> KnowledgeRetrievalResponse:
        raise NotImplementedError(
            "Response translation to internal not typically needed"
        )

    def encode(self, obj: KnowledgeRetrievalResponse) -> Dict[str, Any]:
        result = {
            "edges": [
                {
                    "s": e.s,
                    "p": e.p,
                    "o": e.o,
                    "s-label": e.s_label,
                    "p-label": e.p_label,
                    "o-label": e.o_label,
                    "score": e.score,
                    "concept": e.concept,
                }
                for e in obj.edges
            ],
            "seed-entities": list(obj.seed_entities),
            "concepts": list(obj.concepts),
        }

        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }

        return result

    def encode_with_completion(
        self, obj: KnowledgeRetrievalResponse
    ) -> Tuple[Dict[str, Any], bool]:
        return self.encode(obj), True
