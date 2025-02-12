
import queue
import pulsar
import threading
import time

class Subscriber:

    def __init__(self, pulsar_client, topic, subscription, consumer_name,
                 schema=None, max_size=100):
        self.client = pulsar_client
        self.topic = topic
        self.subscription = subscription
        self.consumer_name = consumer_name
        self.schema = schema
        self.q = {}
        self.full = {}
        self.max_size = max_size
        self.lock = threading.Lock()
        self.running = True

    def start(self):
        self.task = threading.Thread(target=self.run)
        self.task.start()

    def stop(self):
        self.running = False

    def join(self):
        self.task.join()

    def run(self):

        while self.running:

            try:

                consumer = self.client.subscribe(
                    topic=self.topic,
                    subscription_name=self.subscription,
                    consumer_name=self.consumer_name,
                    schema=self.schema,
                )

                while self.running:

                    msg = consumer.receive()

                    # Acknowledge successful reception of the message
                    consumer.acknowledge(msg)

                    try:
                        id = msg.properties()["id"]
                    except:
                        id = None

                    value = msg.value()

                    with self.lock:

                        if id in self.q:
                            try:
                                # FIXME: Timeout means data goes missing
                                self.q[id].put(value, timeout=0.5)
                            except:
                                pass

                        for q in self.full.values():
                            try:
                                # FIXME: Timeout means data goes missing
                                q.put(value, timeout=0.5)
                            except:
                                pass

            except Exception as e:
                print("Exception:", e, flush=True)
         
            # If handler drops out, sleep a retry
            time.sleep(2)

    def subscribe(self, id):

        with self.lock:

            q = queue.Queue(maxsize=self.max_size)
            self.q[id] = q

        return q

    def unsubscribe(self, id):
        
        with self.lock:

            if id in self.q:
#                self.q[id].shutdown(immediate=True)
                del self.q[id]
    
    def subscribe_all(self, id):

        with self.lock:

            q = queue.Queue(maxsize=self.max_size)
            self.full[id] = q

        return q

    def unsubscribe_all(self, id):

        with self.lock:

            if id in self.full:
#                self.full[id].shutdown(immediate=True)
                del self.full[id]

