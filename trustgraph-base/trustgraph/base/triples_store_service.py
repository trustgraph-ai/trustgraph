
"""
Triples store base class
"""

from .. schema import Triples
from .. base import FlowProcessor, ConsumerSpec

default_ident = "triples-write"

class TriplesStoreService(FlowProcessor):

    def __init__(self, **params):

        id = params.get("id")

        super(TriplesStoreService, self).__init__(**params | { "id": id })

        self.register_specification(
            ConsumerSpec(
                name = "input",
                schema = Triples,
                handler = self.on_message
            )
        )

    async def on_message(self, msg, consumer, flow):

        try:

            request = msg.value()

            await self.store_triples(request)

        except TooManyRequests as e:
            raise e

        except Exception as e:
            
            print(f"Exception: {e}")
            raise e

    @staticmethod
    def add_args(parser):

        FlowProcessor.add_args(parser)

