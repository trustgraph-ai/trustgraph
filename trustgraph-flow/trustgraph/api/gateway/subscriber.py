
import queue
import pulsar
import threading
import time

class Subscriber:

    def __init__(self, pulsar_host, topic, subscription, consumer_name,
                 schema=None, max_size=10):
        self.pulsar_host = pulsar_host
        self.topic = topic
        self.subscription = subscription
        self.consumer_name = consumer_name
        self.schema = schema
        self.q = {}
        self.full = {}
        self.max_size = max_size

    def start(self):
        self.task = threading.Thread(target=self.run)
        self.task.start()

    def run(self):

        while True:

            try:

                client = pulsar.Client(
                    self.pulsar_host,
                )

                consumer = client.subscribe(
                    topic=self.topic,
                    subscription_name=self.subscription,
                    consumer_name=self.consumer_name,
                    schema=self.schema,
                )
                
                while True:

                    msg = consumer.receive()

                    print("Received", msg)

                    # Acknowledge successful reception of the message
                    consumer.acknowledge(msg)

                    try:
                        id = msg.properties()["id"]
                    except:
                        id = None

                    value = msg.value()
                    if id in self.q:
                        self.q[id].put(value)

                    for q in self.full.values():
                        q.put(value)

            except Exception as e:
                print("Exception:", e, flush=True)
         
            # If handler drops out, sleep a retry
            time.sleep(2)

    def subscribe(self, id):
        q = queue.Queue(maxsize=self.max_size)
        self.q[id] = q
        return q

    def unsubscribe(self, id):
        if id in self.q:
            del self.q[id]
    
    def subscribe_all(self, id):
        q = queue.Queue(maxsize=self.max_size)
        self.full[id] = q
        return q

    def unsubscribe_all(self, id):
        if id in self.full:
            del self.full[id]

