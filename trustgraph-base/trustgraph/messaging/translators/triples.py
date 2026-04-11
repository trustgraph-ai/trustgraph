from typing import Dict, Any, Tuple, Optional
from ...schema import TriplesQueryRequest, TriplesQueryResponse
from .base import MessageTranslator
from .primitives import ValueTranslator, SubgraphTranslator


class TriplesQueryRequestTranslator(MessageTranslator):
    """Translator for TriplesQueryRequest schema objects"""
    
    def __init__(self):
        self.value_translator = ValueTranslator()
    
    def decode(self, data: Dict[str, Any]) -> TriplesQueryRequest:
        s = self.value_translator.decode(data["s"]) if "s" in data else None
        p = self.value_translator.decode(data["p"]) if "p" in data else None
        o = self.value_translator.decode(data["o"]) if "o" in data else None
        g = data.get("g")  # None=default graph, "*"=all graphs

        return TriplesQueryRequest(
            s=s,
            p=p,
            o=o,
            g=g,
            limit=int(data.get("limit", 10000)),
            user=data.get("user", "trustgraph"),
            collection=data.get("collection", "default"),
            streaming=data.get("streaming", False),
            batch_size=int(data.get("batch-size", 20)),
        )
    
    def encode(self, obj: TriplesQueryRequest) -> Dict[str, Any]:
        result = {
            "limit": obj.limit,
            "user": obj.user,
            "collection": obj.collection,
            "streaming": obj.streaming,
            "batch-size": obj.batch_size,
        }

        if obj.s:
            result["s"] = self.value_translator.encode(obj.s)
        if obj.p:
            result["p"] = self.value_translator.encode(obj.p)
        if obj.o:
            result["o"] = self.value_translator.encode(obj.o)
        if obj.g is not None:
            result["g"] = obj.g

        return result


class TriplesQueryResponseTranslator(MessageTranslator):
    """Translator for TriplesQueryResponse schema objects"""
    
    def __init__(self):
        self.subgraph_translator = SubgraphTranslator()
    
    def decode(self, data: Dict[str, Any]) -> TriplesQueryResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def encode(self, obj: TriplesQueryResponse) -> Dict[str, Any]:
        return {
            "response": self.subgraph_translator.encode(obj.triples)
        }
    
    def encode_with_completion(self, obj: TriplesQueryResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.encode(obj), obj.is_final