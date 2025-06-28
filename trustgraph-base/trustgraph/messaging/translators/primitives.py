from typing import Dict, Any, List
from ...schema import Value, Triple
from .base import Translator


class ValueTranslator(Translator):
    """Translator for Value schema objects"""
    
    def to_pulsar(self, data: Dict[str, Any]) -> Value:
        return Value(value=data["v"], is_uri=data["e"])
    
    def from_pulsar(self, obj: Value) -> Dict[str, Any]:
        return {"v": obj.value, "e": obj.is_uri}


class TripleTranslator(Translator):
    """Translator for Triple schema objects"""
    
    def __init__(self):
        self.value_translator = ValueTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> Triple:
        return Triple(
            s=self.value_translator.to_pulsar(data["s"]),
            p=self.value_translator.to_pulsar(data["p"]),
            o=self.value_translator.to_pulsar(data["o"])
        )
    
    def from_pulsar(self, obj: Triple) -> Dict[str, Any]:
        return {
            "s": self.value_translator.from_pulsar(obj.s),
            "p": self.value_translator.from_pulsar(obj.p),
            "o": self.value_translator.from_pulsar(obj.o)
        }


class SubgraphTranslator(Translator):
    """Translator for lists of Triple objects (subgraphs)"""
    
    def __init__(self):
        self.triple_translator = TripleTranslator()
    
    def to_pulsar(self, data: List[Dict[str, Any]]) -> List[Triple]:
        return [self.triple_translator.to_pulsar(t) for t in data]
    
    def from_pulsar(self, obj: List[Triple]) -> List[Dict[str, Any]]:
        return [self.triple_translator.from_pulsar(t) for t in obj]