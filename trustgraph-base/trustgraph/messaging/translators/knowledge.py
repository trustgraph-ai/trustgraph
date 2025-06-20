from typing import Dict, Any, Tuple, Optional
from ...schema import (
    KnowledgeRequest, KnowledgeResponse, Triples, GraphEmbeddings, 
    Metadata, EntityEmbeddings
)
from .base import MessageTranslator
from .primitives import ValueTranslator, SubgraphTranslator
from .metadata import DocumentMetadataTranslator


class KnowledgeRequestTranslator(MessageTranslator):
    """Translator for KnowledgeRequest schema objects"""
    
    def __init__(self):
        self.value_translator = ValueTranslator()
        self.subgraph_translator = SubgraphTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> KnowledgeRequest:
        triples = None
        if "triples" in data:
            triples = Triples(
                metadata=Metadata(
                    id=data["triples"]["metadata"]["id"],
                    metadata=self.subgraph_translator.to_pulsar(
                        data["triples"]["metadata"]["metadata"]
                    ),
                    user=data["triples"]["metadata"]["user"],
                    collection=data["triples"]["metadata"]["collection"]
                ),
                triples=self.subgraph_translator.to_pulsar(data["triples"]["triples"]),
            )
        
        graph_embeddings = None
        if "graph-embeddings" in data:
            graph_embeddings = GraphEmbeddings(
                metadata=Metadata(
                    id=data["graph-embeddings"]["metadata"]["id"],
                    metadata=self.subgraph_translator.to_pulsar(
                        data["graph-embeddings"]["metadata"]["metadata"]
                    ),
                    user=data["graph-embeddings"]["metadata"]["user"],
                    collection=data["graph-embeddings"]["metadata"]["collection"]
                ),
                entities=[
                    EntityEmbeddings(
                        entity=self.value_translator.to_pulsar(ent["entity"]),
                        vectors=ent["vectors"],
                    )
                    for ent in data["graph-embeddings"]["entities"]
                ]
            )
        
        return KnowledgeRequest(
            operation=data.get("operation"),
            user=data.get("user"),
            id=data.get("id"),
            flow=data.get("flow"),
            collection=data.get("collection"),
            triples=triples,
            graph_embeddings=graph_embeddings,
        )
    
    def from_pulsar(self, obj: KnowledgeRequest) -> Dict[str, Any]:
        result = {}
        
        if obj.operation:
            result["operation"] = obj.operation
        if obj.user:
            result["user"] = obj.user
        if obj.id:
            result["id"] = obj.id
        if obj.flow:
            result["flow"] = obj.flow
        if obj.collection:
            result["collection"] = obj.collection
        
        if obj.triples:
            result["triples"] = {
                "metadata": {
                    "id": obj.triples.metadata.id,
                    "metadata": self.subgraph_translator.from_pulsar(
                        obj.triples.metadata.metadata
                    ),
                    "user": obj.triples.metadata.user,
                    "collection": obj.triples.metadata.collection,
                },
                "triples": self.subgraph_translator.from_pulsar(obj.triples.triples),
            }
        
        if obj.graph_embeddings:
            result["graph-embeddings"] = {
                "metadata": {
                    "id": obj.graph_embeddings.metadata.id,
                    "metadata": self.subgraph_translator.from_pulsar(
                        obj.graph_embeddings.metadata.metadata
                    ),
                    "user": obj.graph_embeddings.metadata.user,
                    "collection": obj.graph_embeddings.metadata.collection,
                },
                "entities": [
                    {
                        "vectors": entity.vectors,
                        "entity": self.value_translator.from_pulsar(entity.entity),
                    }
                    for entity in obj.graph_embeddings.entities
                ],
            }
        
        return result


class KnowledgeResponseTranslator(MessageTranslator):
    """Translator for KnowledgeResponse schema objects"""
    
    def __init__(self):
        self.value_translator = ValueTranslator()
        self.subgraph_translator = SubgraphTranslator()
    
    def to_pulsar(self, data: Dict[str, Any]) -> KnowledgeResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")
    
    def from_pulsar(self, obj: KnowledgeResponse) -> Dict[str, Any]:
        # Response to list operation
        if obj.ids is not None:
            return {"ids": obj.ids}
        
        # Streaming triples response
        if obj.triples:
            return {
                "triples": {
                    "metadata": {
                        "id": obj.triples.metadata.id,
                        "metadata": self.subgraph_translator.from_pulsar(
                            obj.triples.metadata.metadata
                        ),
                        "user": obj.triples.metadata.user,
                        "collection": obj.triples.metadata.collection,
                    },
                    "triples": self.subgraph_translator.from_pulsar(obj.triples.triples),
                }
            }
        
        # Streaming graph embeddings response
        if obj.graph_embeddings:
            return {
                "graph-embeddings": {
                    "metadata": {
                        "id": obj.graph_embeddings.metadata.id,
                        "metadata": self.subgraph_translator.from_pulsar(
                            obj.graph_embeddings.metadata.metadata
                        ),
                        "user": obj.graph_embeddings.metadata.user,
                        "collection": obj.graph_embeddings.metadata.collection,
                    },
                    "entities": [
                        {
                            "vectors": entity.vectors,
                            "entity": self.value_translator.from_pulsar(entity.entity),
                        }
                        for entity in obj.graph_embeddings.entities
                    ],
                }
            }
        
        # End of stream marker
        if obj.eos is True:
            return {"eos": True}
        
        # Empty response (successful delete)
        return {}
    
    def from_response_with_completion(self, obj: KnowledgeResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        response = self.from_pulsar(obj)
        
        # Check if this is a final response
        is_final = (
            obj.ids is not None or  # List response
            obj.eos is True or      # End of stream
            (not obj.triples and not obj.graph_embeddings)  # Empty response
        )
        
        return response, is_final