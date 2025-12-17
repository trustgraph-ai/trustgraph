
import asyncio
import queue
import uuid
import logging

from ... schema import EntityContexts
from ... base import Subscriber

from . serialize import serialize_entity_contexts

# Module logger
logger = logging.getLogger(__name__)

class EntityContextsExport:

    def __init__(
            self, ws, running, backend, queue, consumer, subscriber
    ):

        self.ws = ws
        self.running = running
        self.backend = backend
        self.queue = queue
        self.consumer = consumer
        self.subscriber = subscriber

    async def destroy(self):
        # Step 1: Signal stop to prevent new messages
        self.running.stop()
        
        # Step 2: Wait briefly for in-flight messages
        await asyncio.sleep(0.5)
        
        # Step 3: Unsubscribe and stop subscriber (triggers queue drain)
        if hasattr(self, 'subs'):
            await self.subs.unsubscribe_all(self.id)
            await self.subs.stop()
        
        # Step 4: Close websocket last
        if self.ws and not self.ws.closed:
            await self.ws.close()

    async def receive(self, msg):
        # Ignore incoming info from websocket
        pass

    async def run(self):
        """Enhanced run with better error handling"""
        self.subs = Subscriber(
            backend = self.backend,
            topic = self.queue,
            consumer_name = self.consumer,
            subscription = self.subscriber,
            schema = EntityContexts,
            backpressure_strategy = "block"  # Configurable
        )
        
        await self.subs.start()
        
        self.id = str(uuid.uuid4())
        q = await self.subs.subscribe_all(self.id)
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.running.get():
            try:
                resp = await asyncio.wait_for(q.get(), timeout=0.5)
                await self.ws.send_json(serialize_entity_contexts(resp))
                consecutive_errors = 0  # Reset on success
                
            except asyncio.TimeoutError:
                continue
                
            except queue.Empty:
                continue
                
            except Exception as e:
                logger.error(f"Exception sending to websocket: {str(e)}")
                consecutive_errors += 1
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Too many consecutive errors, shutting down")
                    break
                    
                # Brief pause before retry
                await asyncio.sleep(0.1)
        
        # Graceful cleanup handled in destroy()

