
import logging

from .consumer_spec import ConsumerSpec

logger = logging.getLogger(__name__)


class Flow:
    """
    Runtime representation of a deployed flow process.

    Maintains internal processor states and orchestrates lifecycles
    (start, stop) for inputs (consumers), outputs (producers),
    parameters, and service clients.

    Registration is async and uses the processor's ReceiverPool and
    SenderPool. Producers are registered before consumers so that
    handlers can send output immediately.
    """
    def __init__(self, id, flow, workspace, processor, defn):

        self.id = id
        self.name = flow
        self.workspace = workspace
        self.processor = processor
        self.defn = defn

        self.producer = {}
        self.consumer = {}
        self.parameter = {}

        self.librarian = None

        self._registrations = []

    async def start(self):

        non_consumers = [
            s for s in self.processor.specifications
            if not isinstance(s, ConsumerSpec)
        ]
        consumers = [
            s for s in self.processor.specifications
            if isinstance(s, ConsumerSpec)
        ]

        for spec in non_consumers:
            reg = await spec.register(self, self.processor, self.defn)
            if reg:
                self._registrations.append(reg)

        if self.librarian:
            await self.librarian.start()

        for spec in consumers:
            reg = await spec.register(self, self.processor, self.defn)
            if reg:
                self._registrations.append(reg)

    async def stop(self):

        for reg in self._registrations:
            try:
                if hasattr(reg, 'unregister'):
                    await reg.unregister()
                elif hasattr(reg, 'close'):
                    await reg.close()
                elif hasattr(reg, 'stop'):
                    await reg.stop()
            except Exception as e:
                logger.warning(f"Error unregistering: {e}")

        self._registrations.clear()

        if self.librarian:
            await self.librarian.stop()

    def __call__(self, key):
        if key in self.producer: return self.producer[key]
        if key in self.consumer: return self.consumer[key]
        if key in self.parameter: return self.parameter[key].value
        return None
