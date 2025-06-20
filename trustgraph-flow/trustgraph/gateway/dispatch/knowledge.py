
import base64

from ... schema import KnowledgeRequest, KnowledgeResponse, Triples
from ... schema import GraphEmbeddings, Metadata, EntityEmbeddings
from ... schema import knowledge_request_queue
from ... schema import knowledge_response_queue
from ... messaging import TranslatorRegistry

from . requestor import ServiceRequestor

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

        self.request_translator = TranslatorRegistry.get_request_translator("knowledge")
        self.response_translator = TranslatorRegistry.get_response_translator("knowledge")

    def to_request(self, body):
        return self.request_translator.to_pulsar(body)

    def from_response(self, message):
        return self.response_translator.from_response_with_completion(message)

