from typing import Dict, Any, Tuple, Optional
from ...schema import (
    KnowledgeRequest, KnowledgeResponse, Triples, GraphEmbeddings,
    DocumentEmbeddings, ChunkEmbeddings,
    Metadata, EntityEmbeddings
)
from .base import MessageTranslator
from .primitives import ValueTranslator, SubgraphTranslator


class KnowledgeRequestTranslator(MessageTranslator):
    """Translator for KnowledgeRequest schema objects"""

    def __init__(self):
        self.value_translator = ValueTranslator()
        self.subgraph_translator = SubgraphTranslator()

    def decode(self, data: Dict[str, Any]) -> KnowledgeRequest:
        triples = None
        if "triples" in data:
            triples = Triples(
                metadata=Metadata(
                    id=data["triples"]["metadata"]["id"],
                    root=data["triples"]["metadata"].get("root", ""),
                    collection=data["triples"]["metadata"]["collection"]
                ),
                triples=self.subgraph_translator.decode(data["triples"]["triples"]),
            )

        graph_embeddings = None
        if "graph-embeddings" in data:
            graph_embeddings = GraphEmbeddings(
                metadata=Metadata(
                    id=data["graph-embeddings"]["metadata"]["id"],
                    root=data["graph-embeddings"]["metadata"].get("root", ""),
                    collection=data["graph-embeddings"]["metadata"]["collection"]
                ),
                entities=[
                    EntityEmbeddings(
                        entity=self.value_translator.decode(ent["entity"]),
                        vector=ent["vector"],
                    )
                    for ent in data["graph-embeddings"]["entities"]
                ]
            )

        document_embeddings = None
        if "document-embeddings" in data:
            document_embeddings = DocumentEmbeddings(
                metadata=Metadata(
                    id=data["document-embeddings"]["metadata"]["id"],
                    root=data["document-embeddings"]["metadata"].get("root", ""),
                    collection=data["document-embeddings"]["metadata"]["collection"]
                ),
                chunks=[
                    ChunkEmbeddings(
                        chunk_id=ch["chunk_id"],
                        vector=ch["vector"],
                    )
                    for ch in data["document-embeddings"]["chunks"]
                ]
            )

        return KnowledgeRequest(
            operation=data.get("operation"),
            id=data.get("id"),
            flow=data.get("flow"),
            collection=data.get("collection"),
            triples=triples,
            graph_embeddings=graph_embeddings,
            document_embeddings=document_embeddings,
        )

    def encode(self, obj: KnowledgeRequest) -> Dict[str, Any]:
        result = {}

        if obj.operation:
            result["operation"] = obj.operation
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
                    "root": obj.triples.metadata.root,
                    "collection": obj.triples.metadata.collection,
                },
                "triples": self.subgraph_translator.encode(obj.triples.triples),
            }

        if obj.graph_embeddings:
            result["graph-embeddings"] = {
                "metadata": {
                    "id": obj.graph_embeddings.metadata.id,
                    "root": obj.graph_embeddings.metadata.root,
                    "collection": obj.graph_embeddings.metadata.collection,
                },
                "entities": [
                    {
                        "vector": entity.vector,
                        "entity": self.value_translator.encode(entity.entity),
                    }
                    for entity in obj.graph_embeddings.entities
                ],
            }

        if obj.document_embeddings:
            result["document-embeddings"] = {
                "metadata": {
                    "id": obj.document_embeddings.metadata.id,
                    "root": obj.document_embeddings.metadata.root,
                    "collection": obj.document_embeddings.metadata.collection,
                },
                "chunks": [
                    {
                        "chunk_id": ch.chunk_id,
                        "vector": ch.vector,
                    }
                    for ch in obj.document_embeddings.chunks
                ],
            }

        return result


class KnowledgeResponseTranslator(MessageTranslator):
    """Translator for KnowledgeResponse schema objects"""

    def __init__(self):
        self.value_translator = ValueTranslator()
        self.subgraph_translator = SubgraphTranslator()

    def decode(self, data: Dict[str, Any]) -> KnowledgeResponse:
        raise NotImplementedError("Response translation to Pulsar not typically needed")

    def encode(self, obj: KnowledgeResponse) -> Dict[str, Any]:
        # Response to list operation
        if obj.ids is not None:
            return {"ids": obj.ids}

        # Streaming triples response
        if obj.triples:
            return {
                "triples": {
                    "metadata": {
                        "id": obj.triples.metadata.id,
                        "root": obj.triples.metadata.root,
                        "collection": obj.triples.metadata.collection,
                    },
                    "triples": self.subgraph_translator.encode(obj.triples.triples),
                }
            }

        # Streaming graph embeddings response
        if obj.graph_embeddings:
            return {
                "graph-embeddings": {
                    "metadata": {
                        "id": obj.graph_embeddings.metadata.id,
                        "root": obj.graph_embeddings.metadata.root,
                        "collection": obj.graph_embeddings.metadata.collection,
                    },
                    "entities": [
                        {
                            "vector": entity.vector,
                            "entity": self.value_translator.encode(entity.entity),
                        }
                        for entity in obj.graph_embeddings.entities
                    ],
                }
            }

        # Streaming document embeddings response
        if obj.document_embeddings:
            return {
                "document-embeddings": {
                    "metadata": {
                        "id": obj.document_embeddings.metadata.id,
                        "root": obj.document_embeddings.metadata.root,
                        "collection": obj.document_embeddings.metadata.collection,
                    },
                    "chunks": [
                        {
                            "chunk_id": ch.chunk_id,
                            "vector": ch.vector,
                        }
                        for ch in obj.document_embeddings.chunks
                    ],
                }
            }

        # End of stream marker
        if obj.eos is True:
            return {"eos": True}

        # Empty response (successful delete)
        return {}
    
    def encode_with_completion(self, obj: KnowledgeResponse) -> Tuple[Dict[str, Any], bool]:
        """Returns (response_dict, is_final)"""
        response = self.encode(obj)
        
        # Check if this is a final response
        is_final = (
            obj.ids is not None or  # List response
            obj.eos is True or      # End of stream
            (not obj.triples and not obj.graph_embeddings and not obj.document_embeddings)  # Empty response
        )
        
        return response, is_final