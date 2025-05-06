
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

        print(message)

        response = {
            "eos": message.eos
        }

        if message.ids is not None:
            response["ids"] = message.ids

        if message.triples:
            response["triples"] = serialize_triples(message.triples)

        if message.graph_embeddings:
            response["graph-embeddings"] = serialize_graph_embeddings(
                message.graph_embeddings
            )
        
        return response, True

