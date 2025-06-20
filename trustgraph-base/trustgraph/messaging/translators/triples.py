from typing import Dict, Any, Tuple, Optional
from ...schema import TriplesQueryRequest, TriplesQueryResponse
from .base import MessageTranslator
from .primitives import ValueTranslator, SubgraphTranslator


class TriplesQueryRequestTranslator(MessageTranslator):
    """Translator for TriplesQueryRequest schema objects"""
    
    def __init__(self):
        self.value_translator = ValueTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> TriplesQueryRequest:
        s = self.value_translator.to_pulsar(data["s"]) if "s" in data else None
        p = self.value_translator.to_pulsar(data["p"]) if "p" in data else None
        o = self.value_translator.to_pulsar(data["o"]) if "o" in data else None
        
        return TriplesQueryRequest(
            s=s,
            p=p,
            o=o,
            limit=int(data.get("limit", 10000)),
            user=data.get("user", "trustgraph"),
            collection=data.get("collection", "default")
        )
    
    def from_pulsar(self, obj: TriplesQueryRequest) -> Dict[str, Any]:
        result = {
            "limit": obj.limit,
            "user": obj.user,
            "collection": obj.collection
        }
        
        if obj.s:
            result["s"] = self.value_translator.from_pulsar(obj.s)
        if obj.p:
            result["p"] = self.value_translator.from_pulsar(obj.p)
        if obj.o:
            result["o"] = self.value_translator.from_pulsar(obj.o)
            
        return result


class TriplesQueryResponseTranslator(MessageTranslator):
    """Translator for TriplesQueryResponse schema objects"""
    
    def __init__(self):
        self.subgraph_translator = SubgraphTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> TriplesQueryResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: TriplesQueryResponse) -> Dict[str, Any]:
        return {
            "response": self.subgraph_translator.from_pulsar(obj.triples)
        }
    
    def from_response_with_completion(self, obj: TriplesQueryResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.from_pulsar(obj), True