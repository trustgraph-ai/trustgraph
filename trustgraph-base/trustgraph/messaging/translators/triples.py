from typing import Dict, Any, Tuple, Optional
from ...schema import TriplesQueryRequest, TriplesQueryResponse, UserContext
from ...base.serialization import dict_to_dataclass, dataclass_to_dict
from .base import MessageTranslator
from .primitives import ValueTranslator, SubgraphTranslator


class TriplesQueryRequestTranslator(MessageTranslator):
    """Translator for TriplesQueryRequest schema objects"""
    
    def __init__(self):
        self.value_translator = ValueTranslator()
        self.subgraph_translator = SubgraphTranslator()

    def decode(self, data: Dict[str, Any]) -> TriplesQueryRequest:
        s = self.value_translator.decode(data["s"]) if "s" in data else None
        p = self.value_translator.decode(data["p"]) if "p" in data else None
        o = self.value_translator.decode(data["o"]) if "o" in data else None
        g = data.get("g")
        uc = data.get("user-context")
        triples_data = data.get("triples", [])

        return TriplesQueryRequest(
            s=s,
            p=p,
            o=o,
            g=g,
            limit=int(data.get("limit", 10000)),
            collection=data.get("collection", "default"),
            operation=data.get("operation", ""),
            streaming=data.get("streaming", False),
            batch_size=int(data.get("batch-size", 20)),
            named_graph=data.get("named-graph", ""),
            version=str(data.get("version", "")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            v1=int(data.get("v1", 0)),
            v2=int(data.get("v2", 0)),
            triples=self.subgraph_translator.decode(triples_data) if triples_data else [],
            s_start=data.get("s-start"),
            s_end=data.get("s-end"),
            sync=bool(data.get("sync", False)),
            user_context=dict_to_dataclass(uc, UserContext) if uc else None,
        )

    def encode(self, obj: TriplesQueryRequest) -> Dict[str, Any]:
        result = {
            "limit": obj.limit,
            "collection": obj.collection,
            "streaming": obj.streaming,
            "batch-size": obj.batch_size,
        }

        if obj.operation:
            result["operation"] = obj.operation
        if obj.s:
            result["s"] = self.value_translator.encode(obj.s)
        if obj.p:
            result["p"] = self.value_translator.encode(obj.p)
        if obj.o:
            result["o"] = self.value_translator.encode(obj.o)
        if obj.g is not None:
            result["g"] = obj.g
        if obj.named_graph is not None:
            result["named-graph"] = obj.named_graph
        if obj.version is not None and obj.version != "":
            result["version"] = obj.version
        if obj.name:
            result["name"] = obj.name
        if obj.description:
            result["description"] = obj.description
        if obj.v1 is not None:
            result["v1"] = obj.v1
        if obj.v2 is not None:
            result["v2"] = obj.v2
        if obj.triples:
            result["triples"] = self.subgraph_translator.encode(obj.triples)
        if obj.s_start is not None:
            result["s-start"] = obj.s_start
        if obj.s_end is not None:
            result["s-end"] = obj.s_end
        if obj.sync:
            result["sync"] = obj.sync
        if obj.user_context is not None:
            result["user-context"] = dataclass_to_dict(obj.user_context)

        return result


class TriplesQueryResponseTranslator(MessageTranslator):
    """Translator for TriplesQueryResponse schema objects"""
    
    def __init__(self):
        self.subgraph_translator = SubgraphTranslator()
    
    def decode(self, data: Dict[str, Any]) -> TriplesQueryResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def encode(self, obj: TriplesQueryResponse) -> Dict[str, Any]:
        result = {
            "response": self.subgraph_translator.encode(obj.triples or [])
        }
        if obj.error:
            result["error"] = {
                "type": obj.error.type,
                "message": obj.error.message,
            }
        if obj.version is not None:
            result["version"] = obj.version
        if obj.version_map:
            result["version-map"] = obj.version_map
        if obj.version_log:
            result["version-log"] = [
                {
                    "version": e.version,
                    "created-at": e.created_at,
                    "names": e.names,
                    "description": e.description,
                }
                for e in obj.version_log
            ]
        if obj.added:
            result["added"] = self.subgraph_translator.encode(obj.added)
        if obj.removed:
            result["removed"] = self.subgraph_translator.encode(obj.removed)
        return result

    def encode_with_completion(self, obj: TriplesQueryResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        return self.encode(obj), obj.is_final