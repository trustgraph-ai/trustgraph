
"""
Triples query service.  Input is a (s, p, o) triple, some values may be
null.  Output is a list of triples.
"""

from .... schema import TriplesQueryRequest, TriplesQueryResponse, Error
from .... schema import Value, Triple

from .... base import FlowProcessor, TriplesQueryService, ConsumerSpec
from .... base import ProducerSpec

default_ident = "triples-query"

class TriplesQueryService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        super(TriplesStoreService, self).__init__(**params | { "id": id })

        self.register_specification(
            ConsumerSpec(
                name = "request",
                schema = TriplesQueryRequest,
                handler = self.on_message
            )
        )

        self.register_specification(
            ProducerSpec(
                name = "response",
                schema = TriplesQueryResponse,
            )
        )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            # Sender-produced ID
            id = msg.properties()["id"]

            print(f"Handling input {id}...", flush=True)

            triples = self.query_triples(request)

            print("Send response...", flush=True)
            r = TriplesQueryResponse(triples=triples, error=None)
            await flow("response").send(r, properties={"id": id})

            print("Done.", flush=True)

        except Exception as e:

            print(f"Exception: {e}")

            print("Send error response...", flush=True)

            r = TriplesQueryResponse(
                error = Error(
                    type = "triples-query-error",
                    message = str(e),
                ),
                triples = None,
            )

            await flow("response").send(r, properties={"id": id})

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

def run():

    Processor.launch(default_ident, __doc__)

