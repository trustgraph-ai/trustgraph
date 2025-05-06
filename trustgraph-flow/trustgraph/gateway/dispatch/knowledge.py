
import base64

from ... schema import KnowledgeRequest, KnowledgeResponse
from ... schema import knowledge_request_queue
from ... schema import knowledge_response_queue

from . requestor import ServiceRequestor
from . serialize import serialize_graph_embeddings
from . serialize import serialize_triples
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

        return KnowledgeRequest(
            operation = body.get("operation", None),
            user = body.get("user", None),
            id = body.get("id", None),
        )

    def from_response(self, message):

        print("Processing message")

        # Response to list, 
        if message.ids is not None:
            print("-> IDS")
            return {
                "ids": message.ids
            }, True

        if message.triples:
            print("-> triples")
            return {
                "triples": serialize_triples(message.triples)
            }, False

        if message.graph_embeddings:
            print("-> ge")
            return {
                "graph-embeddings": serialize_graph_embeddings(
                    message.graph_embeddings
                )
            }, False

        if message.eos is True:
            print("-> eos")
            return {
                "eos": True
            }, True

        # Empty case, return from successful delete.
        return {}, True

