
import base64

from ... schema import KnowledgeRequest, KnowledgeResponse, Triples
from ... schema import GraphEmbeddings, Metadata, EntityEmbeddings
from ... schema import knowledge_request_queue
from ... schema import knowledge_response_queue

from . requestor import ServiceRequestor
from . serialize import serialize_graph_embeddings
from . serialize import serialize_triples, to_subgraph, to_value
from . serialize import to_document_metadata, to_processing_metadata

class KnowledgeRequestor(ServiceRequestor):
    def __init__(self, pulsar_client, consumer, subscriber, timeout=120):

        super(KnowledgeRequestor, self).__init__(
            pulsar_client=pulsar_client,
            consumer_name = consumer,
            subscription = subscriber,
            request_queue=knowledge_request_queue,
            response_queue=knowledge_response_queue,
            request_schema=KnowledgeRequest,
            response_schema=KnowledgeResponse,
            timeout=timeout,
        )

    def to_request(self, body):

        if "triples" in body:
            triples = Triples(
                metadata=Metadata(
                    id = body["triples"]["metadata"]["id"],
                    metadata = to_subgraph(body["triples"]["metadata"]["metadata"]),
                    user = body["triples"]["metadata"]["user"],
                ),
                triples = to_subgraph(body["triples"]["triples"]),
            )
        else:
            triples = None

        if "graph-embeddings" in body:
            ge = GraphEmbeddings(
                metadata = Metadata(
                    id = body["graph-embeddings"]["metadata"]["id"],
                    metadata = to_subgraph(body["graph-embeddings"]["metadata"]["metadata"]),
                    user = body["graph-embeddings"]["metadata"]["user"],
                ),
                entities=[
                    EntityEmbeddings(
                        entity = to_value(ent["entity"]),
                        vectors = ent["vectors"],
                    )
                    for ent in body["graph-embeddings"]["entities"]
                ]
            )
        else:
            ge = None

        return KnowledgeRequest(
            operation = body.get("operation", None),
            user = body.get("user", None),
            id = body.get("id", None),
            flow = body.get("flow", None),
            collection = body.get("collection", None),
            triples = triples,
            graph_embeddings = ge,
        )

    def from_response(self, message):

        # Response to list, 
        if message.ids is not None:
            return {
                "ids": message.ids
            }, True

        if message.triples:
            return {
                "triples": serialize_triples(message.triples)
            }, False

        if message.graph_embeddings:
            return {
                "graph-embeddings": serialize_graph_embeddings(
                    message.graph_embeddings
                )
            }, False

        if message.eos is True:
            return {
                "eos": True
            }, True

        # Empty case, return from successful delete.
        return {}, True

