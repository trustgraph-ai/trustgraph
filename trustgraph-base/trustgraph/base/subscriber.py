
# Subscriber is similar to consumer: It provides a service to take stuff
# off of a queue and make it available using an internal broker system,
# so suitable for when multiple recipients are reading from the same queue

from pulsar.schema import JsonSchema
import asyncio
import _pulsar
import time
import logging
import uuid

# Module logger
logger = logging.getLogger(__name__)

class Subscriber:

    def __init__(self, client, topic, subscription, consumer_name,
                 schema=None, max_size=100, metrics=None,
                 backpressure_strategy="block", drain_timeout=5.0):
        self.client = client
        self.topic = topic
        self.subscription = subscription
        self.consumer_name = consumer_name
        self.schema = schema
        self.q = {}
        self.full = {}
        self.max_size = max_size
        self.lock = asyncio.Lock()
        self.running = True
        self.draining = False  # New state for graceful shutdown
        self.metrics = metrics
        self.task = None
        self.backpressure_strategy = backpressure_strategy
        self.drain_timeout = drain_timeout
        self.pending_acks = {}  # Track messages awaiting delivery

        self.consumer = None

    def __del__(self):

        self.running = False

    async def start(self):

        self.consumer = self.client.subscribe(
            topic = self.topic,
            subscription_name = self.subscription,
            consumer_name = self.consumer_name,
            schema = JsonSchema(self.schema),
        )

        self.task = asyncio.create_task(self.run())

    async def stop(self):
        """Initiate graceful shutdown with draining"""
        self.running = False
        self.draining = True

        if self.task:
            # Wait for run() to complete draining
            await self.task

    async def join(self):
        await self.stop()

        if self.task:
            await self.task

    async def run(self):
        """Enhanced run method with integrated draining logic"""
        while self.running or self.draining:

            if self.metrics:
                self.metrics.state("stopped")

            try:

                if self.metrics:
                    self.metrics.state("running")

                logger.info("Subscriber running...")
                drain_end_time = None

                while self.running or self.draining:
                    # Start drain timeout when entering drain mode
                    if self.draining and drain_end_time is None:
                        drain_end_time = time.time() + self.drain_timeout
                        logger.info(f"Subscriber entering drain mode, timeout={self.drain_timeout}s")
                        
                        # Stop accepting new messages from Pulsar during drain
                        if self.consumer:
                            self.consumer.pause_message_listener()
                    
                    # Check drain timeout
                    if self.draining and drain_end_time and time.time() > drain_end_time:
                        async with self.lock:
                            total_pending = sum(
                                q.qsize() for q in 
                                list(self.q.values()) + list(self.full.values())
                            )
                            if total_pending > 0:
                                logger.warning(f"Drain timeout reached with {total_pending} messages in queues")
                        self.draining = False
                        break
                    
                    # Check if we can exit drain mode
                    if self.draining:
                        async with self.lock:
                            all_empty = all(
                                q.empty() for q in 
                                list(self.q.values()) + list(self.full.values())
                            )
                            if all_empty and len(self.pending_acks) == 0:
                                logger.info("Subscriber queues drained successfully")
                                self.draining = False
                                break
                    
                    # Process messages only if not draining
                    if not self.draining:
                        try:
                            msg = await asyncio.to_thread(
                                self.consumer.receive,
                                timeout_millis=250
                            )
                        except _pulsar.Timeout:
                            continue
                        except Exception as e:
                            logger.error(f"Exception in subscriber receive: {e}", exc_info=True)
                            raise e

                        if self.metrics:
                            self.metrics.received()

                        # Process the message with deferred acknowledgment
                        await self._process_message(msg)
                    else:
                        # During draining, just wait for queues to empty
                        await asyncio.sleep(0.1)


            except Exception as e:
                logger.error(f"Subscriber exception: {e}", exc_info=True)

            finally:
                # Negative acknowledge any pending messages
                for msg in self.pending_acks.values():
                    self.consumer.negative_acknowledge(msg)
                self.pending_acks.clear()

                if self.consumer:
                    self.consumer.unsubscribe()
                    self.consumer.close()
                    self.consumer = None
                
         
            if self.metrics:
                self.metrics.state("stopped")

            if not self.running and not self.draining:
                return
            
            # If handler drops out, sleep a retry
            await asyncio.sleep(1)

    async def subscribe(self, id):

        async with self.lock:

            q = asyncio.Queue(maxsize=self.max_size)
            self.q[id] = q

        return q

    async def unsubscribe(self, id):
        
        async with self.lock:

            if id in self.q:
#                self.q[id].shutdown(immediate=True)
                del self.q[id]
    
    async def subscribe_all(self, id):

        async with self.lock:

            q = asyncio.Queue(maxsize=self.max_size)
            self.full[id] = q

        return q

    async def unsubscribe_all(self, id):

        async with self.lock:

            if id in self.full:
#                self.full[id].shutdown(immediate=True)
                del self.full[id]

    async def _process_message(self, msg):
        """Process a single message with deferred acknowledgment"""
        # Store message for later acknowledgment
        msg_id = str(uuid.uuid4())
        self.pending_acks[msg_id] = msg
        
        try:
            id = msg.properties()["id"]
        except:
            id = None
            
        value = msg.value()
        delivery_success = False
        
        async with self.lock:
            # Deliver to specific subscribers
            if id in self.q:
                delivery_success = await self._deliver_to_queue(
                    self.q[id], value
                )
            
            # Deliver to all subscribers
            for q in self.full.values():
                if await self._deliver_to_queue(q, value):
                    delivery_success = True
        
        # Acknowledge only on successful delivery
        if delivery_success:
            self.consumer.acknowledge(msg)
            del self.pending_acks[msg_id]
        else:
            # Negative acknowledge for retry
            self.consumer.negative_acknowledge(msg)
            del self.pending_acks[msg_id]
                
    async def _deliver_to_queue(self, queue, value):
        """Deliver message to queue with backpressure handling"""
        try:
            if self.backpressure_strategy == "block":
                # Block until space available (no timeout)
                await queue.put(value)
                return True
                
            elif self.backpressure_strategy == "drop_oldest":
                # Drop oldest message if queue full
                if queue.full():
                    try:
                        queue.get_nowait()
                        if self.metrics:
                            self.metrics.dropped()
                    except asyncio.QueueEmpty:
                        pass
                await queue.put(value)
                return True
                
            elif self.backpressure_strategy == "drop_new":
                # Drop new message if queue full
                if queue.full():
                    if self.metrics:
                        self.metrics.dropped()
                    return False
                await queue.put(value)
                return True
                
        except Exception as e:
            logger.error(f"Failed to deliver message: {e}")
            return False

