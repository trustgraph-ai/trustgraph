# 导入/导出 优雅关闭 技术规范

## 问题陈述

TrustGraph 网关在导入和导出操作中，在 WebSocket 连接关闭时，目前存在消息丢失的问题。 这是由于存在竞争条件，导致正在传输的消息在到达目的地之前被丢弃（对于导入，是丢弃到 Pulsar 队列的消息；对于导出，是丢弃到 WebSocket 客户端的消息）。

### 导入端问题
1. 发布者的 asyncio.Queue 缓冲区在关闭时未被清空
2. 在确保所有排队的消息到达 Pulsar 之前，WebSocket 连接关闭
3. 没有用于确认消息成功传递的机制

### 导出端问题
1. 消息在成功传递到客户端之前，已在 Pulsar 中得到确认
2. 预定义的超时时间会导致队列已满时消息丢失
3. 没有用于处理慢速消费者的反压机制
4. 存在多个缓冲区，数据可能在此处丢失

## 架构概述

```
Import Flow:
Client -> Websocket -> TriplesImport -> Publisher -> Pulsar Queue

Export Flow:
Pulsar Queue -> Subscriber -> TriplesExport -> Websocket -> Client
```

## 建议的修复方案

### 1. 发布者改进（导入端）

#### A. 优雅的队列清空

**文件**: `trustgraph-base/trustgraph/base/publisher.py`

```python
class Publisher:
    def __init__(self, client, topic, schema=None, max_size=10,
                 chunking_enabled=True, drain_timeout=5.0):
        self.client = client
        self.topic = topic
        self.schema = schema
        self.q = asyncio.Queue(maxsize=max_size)
        self.chunking_enabled = chunking_enabled
        self.running = True
        self.draining = False  # New state for graceful shutdown
        self.task = None
        self.drain_timeout = drain_timeout

    async def stop(self):
        """Initiate graceful shutdown with draining"""
        self.running = False
        self.draining = True
        
        if self.task:
            # Wait for run() to complete draining
            await self.task

    async def run(self):
        """Enhanced run method with integrated draining logic"""
        while self.running or self.draining:
            try:
                producer = self.client.create_producer(
                    topic=self.topic,
                    schema=JsonSchema(self.schema),
                    chunking_enabled=self.chunking_enabled,
                )

                drain_end_time = None
                
                while self.running or self.draining:
                    try:
                        # Start drain timeout when entering drain mode
                        if self.draining and drain_end_time is None:
                            drain_end_time = time.time() + self.drain_timeout
                            logger.info(f"Publisher entering drain mode, timeout={self.drain_timeout}s")
                        
                        # Check drain timeout
                        if self.draining and time.time() > drain_end_time:
                            if not self.q.empty():
                                logger.warning(f"Drain timeout reached with {self.q.qsize()} messages remaining")
                            self.draining = False
                            break
                        
                        # Calculate wait timeout based on mode
                        if self.draining:
                            # Shorter timeout during draining to exit quickly when empty
                            timeout = min(0.1, drain_end_time - time.time())
                        else:
                            # Normal operation timeout
                            timeout = 0.25
                        
                        # Get message from queue
                        id, item = await asyncio.wait_for(
                            self.q.get(),
                            timeout=timeout
                        )
                        
                        # Send the message (single place for sending)
                        if id:
                            producer.send(item, { "id": id })
                        else:
                            producer.send(item)
                            
                    except asyncio.TimeoutError:
                        # If draining and queue is empty, we're done
                        if self.draining and self.q.empty():
                            logger.info("Publisher queue drained successfully")
                            self.draining = False
                            break
                        continue
                        
                    except asyncio.QueueEmpty:
                        # If draining and queue is empty, we're done  
                        if self.draining and self.q.empty():
                            logger.info("Publisher queue drained successfully")
                            self.draining = False
                            break
                        continue
                
                # Flush producer before closing
                if producer:
                    producer.flush()
                    producer.close()

            except Exception as e:
                logger.error(f"Exception in publisher: {e}", exc_info=True)

            if not self.running and not self.draining:
                return

            # If handler drops out, sleep a retry
            await asyncio.sleep(1)

    async def send(self, id, item):
        """Send still works normally - just adds to queue"""
        if self.draining:
            # Optionally reject new messages during drain
            raise RuntimeError("Publisher is shutting down, not accepting new messages")
        await self.q.put((id, item))
```

**主要设计优势：**
**单一发送位置：** 所有 `producer.send()` 调用都发生在 `run()` 方法内的单一位置。
**清晰的状态机：** 三个明确的状态 - 运行中、正在排空、已停止。
**超时保护：** 在排空过程中不会无限期挂起。
**更好的可观察性：** 清晰地记录排空进度和状态转换。
**可选的消息拒绝：** 可以在关闭阶段拒绝新的消息。

#### B. 改进的关闭顺序

**文件：** `trustgraph-flow/trustgraph/gateway/dispatch/triples_import.py`

```python
class TriplesImport:
    async def destroy(self):
        """Enhanced destroy with proper shutdown order"""
        # Step 1: Stop accepting new messages
        self.running.stop()
        
        # Step 2: Wait for publisher to drain its queue
        logger.info("Draining publisher queue...")
        await self.publisher.stop()
        
        # Step 3: Close websocket only after queue is drained
        if self.ws:
            await self.ws.close()
```

### 2. 订阅者改进（导出端）

#### A. 集成排空模式

**文件**: `trustgraph-base/trustgraph/base/subscriber.py`

```python
class Subscriber:
    def __init__(self, client, topic, subscription, consumer_name,
                 schema=None, max_size=100, metrics=None,
                 backpressure_strategy="block", drain_timeout=5.0):
        # ... existing init ...
        self.backpressure_strategy = backpressure_strategy
        self.running = True
        self.draining = False  # New state for graceful shutdown
        self.drain_timeout = drain_timeout
        self.pending_acks = {}  # Track messages awaiting delivery
        
    async def stop(self):
        """Initiate graceful shutdown with draining"""
        self.running = False
        self.draining = True
        
        if self.task:
            # Wait for run() to complete draining
            await self.task
            
    async def run(self):
        """Enhanced run method with integrated draining logic"""
        while self.running or self.draining:
            if self.metrics:
                self.metrics.state("stopped")

            try:
                self.consumer = self.client.subscribe(
                    topic = self.topic,
                    subscription_name = self.subscription,
                    consumer_name = self.consumer_name,
                    schema = JsonSchema(self.schema),
                )

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
                        self.consumer.pause_message_listener()
                    
                    # Check drain timeout
                    if self.draining and time.time() > drain_end_time:
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

                        # Process the message
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
```

**主要设计优势（与发布者模式匹配）：**
**单一处理位置：** 所有消息处理都在 `run()` 方法中进行。
**清晰的状态机：** 三个明确的状态 - 运行中、正在排空、已停止。
**排空期间暂停：** 在排空现有队列时，停止从 Pulsar 接收新消息。
**超时保护：** 在排空过程中不会无限期挂起。
**正确的清理：** 在关闭时，会对任何未发送的消息进行否定确认。

#### B. 导出处理程序改进

**文件：** `trustgraph-flow/trustgraph/gateway/dispatch/triples_export.py`

```python
class TriplesExport:
    async def destroy(self):
        """Enhanced destroy with graceful shutdown"""
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
            
    async def run(self):
        """Enhanced run with better error handling"""
        self.subs = Subscriber(
            client = self.pulsar_client, 
            topic = self.queue,
            consumer_name = self.consumer, 
            subscription = self.subscriber,
            schema = Triples,
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
                await self.ws.send_json(serialize_triples(resp))
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
```

### 3. Socket 级别改进

**文件**: `trustgraph-flow/trustgraph/gateway/endpoint/socket.py`

```python
class SocketEndpoint:
    async def listener(self, ws, dispatcher, running):
        """Enhanced listener with graceful shutdown"""
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                await dispatcher.receive(msg)
                continue
            elif msg.type == WSMsgType.BINARY:
                await dispatcher.receive(msg)
                continue
            else:
                # Graceful shutdown on close
                logger.info("Websocket closing, initiating graceful shutdown")
                running.stop()
                
                # Allow time for dispatcher cleanup
                await asyncio.sleep(1.0)
                break
                
    async def handle(self, request):
        """Enhanced handler with better cleanup"""
        # ... existing setup code ...
        
        try:
            async with asyncio.TaskGroup() as tg:
                running = Running()
                
                dispatcher = await self.dispatcher(
                    ws, running, request.match_info
                )
                
                worker_task = tg.create_task(
                    self.worker(ws, dispatcher, running)
                )
                
                lsnr_task = tg.create_task(
                    self.listener(ws, dispatcher, running)
                )
                
        except ExceptionGroup as e:
            logger.error("Exception group occurred:", exc_info=True)
            
            # Attempt graceful dispatcher shutdown
            try:
                await asyncio.wait_for(
                    dispatcher.destroy(), 
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("Dispatcher shutdown timed out")
            except Exception as de:
                logger.error(f"Error during dispatcher cleanup: {de}")
                
        except Exception as e:
            logger.error(f"Socket exception: {e}", exc_info=True)
            
        finally:
            # Ensure dispatcher cleanup
            if dispatcher and hasattr(dispatcher, 'destroy'):
                try:
                    await dispatcher.destroy()
                except:
                    pass
                    
            # Ensure websocket is closed
            if ws and not ws.closed:
                await ws.close()
                
        return ws
```

## 配置选项

添加配置支持，用于调整行为：

```python
# config.py
class GracefulShutdownConfig:
    # Publisher settings
    PUBLISHER_DRAIN_TIMEOUT = 5.0  # Seconds to wait for queue drain
    PUBLISHER_FLUSH_TIMEOUT = 2.0  # Producer flush timeout
    
    # Subscriber settings  
    SUBSCRIBER_DRAIN_TIMEOUT = 5.0  # Seconds to wait for queue drain
    BACKPRESSURE_STRATEGY = "block"  # Options: "block", "drop_oldest", "drop_new"
    SUBSCRIBER_MAX_QUEUE_SIZE = 100  # Maximum queue size before backpressure
    
    # Socket settings
    SHUTDOWN_GRACE_PERIOD = 1.0  # Seconds to wait for graceful shutdown
    MAX_CONSECUTIVE_ERRORS = 5  # Maximum errors before forced shutdown
    
    # Monitoring
    LOG_QUEUE_STATS = True  # Log queue statistics on shutdown
    METRICS_ENABLED = True  # Enable metrics collection
```

## 测试策略

### 单元测试

```python
async def test_publisher_queue_drain():
    """Verify Publisher drains queue on shutdown"""
    publisher = Publisher(...)
    
    # Fill queue with messages
    for i in range(10):
        await publisher.send(f"id-{i}", {"data": i})
    
    # Stop publisher
    await publisher.stop()
    
    # Verify all messages were sent
    assert publisher.q.empty()
    assert mock_producer.send.call_count == 10

async def test_subscriber_deferred_ack():
    """Verify Subscriber only acks on successful delivery"""
    subscriber = Subscriber(..., backpressure_strategy="drop_new")
    
    # Fill queue to capacity
    queue = await subscriber.subscribe("test")
    for i in range(100):
        await queue.put({"data": i})
    
    # Try to add message when full
    msg = create_mock_message()
    await subscriber._process_message(msg)
    
    # Verify negative acknowledgment
    assert msg.negative_acknowledge.called
    assert not msg.acknowledge.called
```

### 集成测试

```python
async def test_import_graceful_shutdown():
    """Test import path handles shutdown gracefully"""
    # Setup
    import_handler = TriplesImport(...)
    await import_handler.start()
    
    # Send messages
    messages = []
    for i in range(100):
        msg = {"metadata": {...}, "triples": [...]}
        await import_handler.receive(msg)
        messages.append(msg)
    
    # Shutdown while messages in flight
    await import_handler.destroy()
    
    # Verify all messages reached Pulsar
    received = await pulsar_consumer.receive_all()
    assert len(received) == 100

async def test_export_no_message_loss():
    """Test export path doesn't lose acknowledged messages"""
    # Setup Pulsar with test messages
    for i in range(100):
        await pulsar_producer.send({"data": i})
    
    # Start export handler
    export_handler = TriplesExport(...)
    export_task = asyncio.create_task(export_handler.run())
    
    # Receive some messages
    received = []
    for _ in range(50):
        msg = await websocket.receive()
        received.append(msg)
    
    # Force shutdown
    await export_handler.destroy()
    
    # Continue receiving until websocket closes
    while not websocket.closed:
        try:
            msg = await websocket.receive()
            received.append(msg)
        except:
            break
    
    # Verify no acknowledged messages were lost
    assert len(received) >= 50
```

## 部署计划

### 第一阶段：关键修复（第一周）
修复订阅者确认时序问题（防止消息丢失）
添加发布者队列排空功能
部署到测试环境

### 第二阶段：平滑关闭（第二周）
实施关闭协调
添加反压策略
性能测试

### 第三阶段：监控与调优（第三周）
添加队列深度的指标
添加消息丢失的告警
根据生产数据调整超时值

## 监控与告警

### 跟踪指标
`publisher.queue.depth` - 当前发布者队列大小
`publisher.messages.dropped` - 关闭期间丢失的消息数量
`subscriber.messages.negatively_acknowledged` - 失败的交付
`websocket.graceful_shutdowns` - 成功的平滑关闭
`websocket.forced_shutdowns` - 强制/超时关闭

### 告警
发布者队列深度超过 80% 的容量
关闭期间出现任何消息丢失
订阅者否定确认率 > 1%
关闭超时

## 向后兼容性

所有更改都保持向后兼容性：
在没有配置的情况下，默认行为保持不变
现有部署继续正常运行
如果新的功能不可用，则会进行优雅降级

## 安全注意事项

没有引入新的攻击向量
反压可防止内存耗尽攻击
可配置的限制可防止资源滥用

## 性能影响

正常运行期间的开销很小
关闭可能需要长达 5 秒（可配置）
内存使用量受队列大小限制
CPU 影响可以忽略不计（<1% 的增加）