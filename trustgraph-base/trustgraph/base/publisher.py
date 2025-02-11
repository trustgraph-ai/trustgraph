
import queue
import time
import pulsar
import threading

class Publisher:

    def __init__(self, pulsar_host, topic, schema=None, max_size=10,
                 chunking_enabled=True, listener=None):
        self.pulsar_host = pulsar_host
        self.topic = topic
        self.schema = schema
        self.q = queue.Queue(maxsize=max_size)
        self.chunking_enabled = chunking_enabled
        self.listener_name = listener
        self.running = True

    def start(self):
        self.task = threading.Thread(target=self.run)
        self.task.start()

    def stop(self):
        self.running = False

    def join(self):
        self.stop()
        self.task.join()

    def run(self):

        while self.running:

            try:

                client = pulsar.Client(
                    self.pulsar_host, listener_name=self.listener_name
                )

                producer = client.create_producer(
                    topic=self.topic,
                    schema=self.schema,
                    chunking_enabled=self.chunking_enabled,
                )

                while self.running:

                    try:
                        id, item = self.q.get(timeout=0.5)
                    except queue.Empty:
                        continue

                    if id:
                        producer.send(item, { "id": id })
                    else:
                        producer.send(item)

            except Exception as e:
                print("Exception:", e, flush=True)

            # If handler drops out, sleep a retry
            time.sleep(2)

    def send(self, id, msg):
        self.q.put((id, msg))

        
