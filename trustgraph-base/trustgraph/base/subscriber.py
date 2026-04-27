
# Subscriber is similar to consumer: It provides a service to take stuff
# off of a queue and make it available using an internal broker system,
# so suitable for when multiple recipients are reading from the same queue

import asyncio
import time
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

# Module logger
logger = logging.getLogger(__name__)

# Timeout exception - can come from different backends
class TimeoutError(Exception):
    pass

class Subscriber:

    def __init__(self, backend, topic, subscription, consumer_name,
                 schema=None, max_size=100, metrics=None,
                 backpressure_strategy="block", drain_timeout=5.0):
        self.backend = backend  # Changed from 'client' to 'backend'
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
        self.executor = None

        # Readiness barrier — completed by run() once the underlying
        # backend consumer is fully connected and bound. start() awaits
        # this so callers know any subsequently published request will
        # have a queue ready to receive its response. Without this,
        # ephemeral per-subscriber response queues (RabbitMQ auto-delete
        # exclusive queues) would race the request and lose the reply.
        # A Future is used (rather than an Event) so that a first-attempt
        # connection failure can be propagated to start() as an exception.
        self._ready = None  # created in start() so we have a running loop

    def __del__(self):

        self.running = False

    async def start(self):

        self._ready = asyncio.get_event_loop().create_future()
        self.task = asyncio.create_task(self.run())

        # Block until run() signals readiness OR exits. The future
        # carries the outcome of the first connect attempt: a value on
        # success, an exception on first-attempt failure. If run() exits
        # without ever signalling (e.g. cancelled, or a code path bug),
        # we surface that as a clear RuntimeError rather than hanging
        # forever waiting on the future.
        ready_wait = asyncio.ensure_future(
            asyncio.shield(self._ready)
        )
        try:
            await asyncio.wait(
                {self.task, ready_wait},
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            ready_wait.cancel()

        if self._ready.done():
            # Re-raise first-attempt connect failure if any.
            self._ready.result()
            return

        # run() exited before _ready was settled. Propagate its exception
        # if it had one, otherwise raise a generic readiness error.
        if self.task.done() and self.task.exception() is not None:
            raise self.task.exception()
        raise RuntimeError(
            "Subscriber.run() exited before signalling readiness"
        )

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
        first_attempt = True
        while self.running or self.draining:

            if self.metrics:
                self.metrics.state("stopped")

            try:

                # Create consumer and dedicated thread if needed
                # (first run or after failure)
                if self.consumer is None:
                    self.executor = ThreadPoolExecutor(max_workers=1)
                    loop = asyncio.get_event_loop()
                    self.consumer = await loop.run_in_executor(
                        self.executor,
                        lambda: self.backend.create_consumer(
                            topic=self.topic,
                            subscription=self.subscription,
                            schema=self.schema,
                        ),
                    )

                    # Eagerly bind the queue. For backends that connect
                    # lazily on first receive (RabbitMQ), this is what
                    # closes the request/response setup race — without
                    # it the response queue is not bound until later and
                    # any reply published in the meantime is dropped.
                    await loop.run_in_executor(
                        self.executor,
                        lambda: self.consumer.ensure_connected(),
                    )

                if self.metrics:
                    self.metrics.state("running")

                logger.info("Subscriber running...")

                # Signal start() that the consumer is ready. This must
                # happen AFTER ensure_connected() above so callers can
                # safely publish requests immediately after start() returns.
                if first_attempt and not self._ready.done():
                    self._ready.set_result(None)
                    first_attempt = False
                drain_end_time = None

                while self.running or self.draining:
                    # Start drain timeout when entering drain mode
                    if self.draining and drain_end_time is None:
                        drain_end_time = time.time() + self.drain_timeout
                        logger.info(f"Subscriber entering drain mode, timeout={self.drain_timeout}s")

                        # Stop accepting new messages during drain
                        # Note: Not all backends support pausing message listeners
                        if self.consumer and hasattr(self.consumer, 'pause_message_listener'):
                            try:
                                self.consumer.pause_message_listener()
                            except Exception:
                                # Not all consumers support message listeners
                                pass
                    
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
                            loop = asyncio.get_event_loop()
                            msg = await loop.run_in_executor(
                                self.executor,
                                lambda: self.consumer.receive(
                                    timeout_millis=250
                                ),
                            )
                        except Exception as e:
                            # Handle timeout from any backend
                            if 'timeout' in str(type(e)).lower() or 'timeout' in str(e).lower():
                                continue
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

                # First-attempt connection failure: propagate to start()
                # so the caller can decide what to do (retry, give up).
                # Subsequent failures use the existing retry-with-backoff
                # path so a long-lived subscriber survives broker blips.
                if first_attempt and not self._ready.done():
                    self._ready.set_exception(e)
                    first_attempt = False
                    # Falls through into finally for cleanup, then the
                    # outer return below ends run() so start() unblocks.

            finally:
                # Negative acknowledge any pending messages
                for msg in self.pending_acks.values():
                    try:
                        self.consumer.negative_acknowledge(msg)
                    except Exception:
                        pass  # Consumer already closed or error
                self.pending_acks.clear()

                if self.consumer:
                    if hasattr(self.consumer, 'unsubscribe'):
                        try:
                            self.consumer.unsubscribe()
                        except Exception:
                            pass  # Already closed or error
                    try:
                        self.consumer.close()
                    except Exception:
                        pass  # Already closed or error
                    self.consumer = None

                if self.executor:
                    self.executor.shutdown(wait=False)
                    self.executor = None

            if self.metrics:
                self.metrics.state("stopped")

            if not self.running and not self.draining:
                return

            # If start() has already returned with an exception there is
            # nothing more to do — exit run() rather than busy-retry.
            if self._ready.done() and self._ready.exception() is not None:
                return

            # Sleep before retry
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
        has_matching_waiter = False

        async with self.lock:
            # Deliver to specific subscribers
            if id in self.q:
                has_matching_waiter = True
                delivery_success = await self._deliver_to_queue(
                    self.q[id], value
                )

            # Deliver to all subscribers
            for q in self.full.values():
                has_matching_waiter = True
                if await self._deliver_to_queue(q, value):
                    delivery_success = True

        # Always acknowledge the message to prevent redelivery storms
        # on shared topics. Negative acknowledging orphaned messages
        # (no matching waiter) causes immediate redelivery to all
        # subscribers, none of whom can handle it either.
        self.consumer.acknowledge(msg)
        del self.pending_acks[msg_id]

        if not delivery_success:
            if not has_matching_waiter:
                # Message arrived for a waiter that no longer exists
                # (likely due to client disconnect or timeout)
                logger.debug(
                    f"Discarding orphaned message with id={id} - "
                    "no matching waiter"
                )
            else:
                # Delivery failed (e.g., queue full with drop_new strategy)
                logger.debug(
                    f"Message with id={id} dropped due to backpressure"
                )
                
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

