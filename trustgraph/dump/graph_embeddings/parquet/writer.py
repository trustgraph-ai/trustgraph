
import threading
import queue
import time
import uuid
import pyarrow as pa
import pyarrow.parquet as pq

class ParquetWriter:

    def __init__(self, directory, file_template, rotation_time):
        self.directory = directory
        self.file_template = file_template
        self.rotation_time = rotation_time

        self.q = queue.Queue()

        self.running = True

        self.thread = threading.Thread(target=(self.writer_thread))
        self.thread.start()

    def writer_thread(self):

        items = []

        timeout = None

        while self.running:

            try:

                item = self.q.get(timeout=1)

                if timeout == None:
                    timeout = time.time() + self.rotation_time

                items.append(item)

            except queue.Empty:
                pass

            if timeout:
                if time.time() > timeout:

                    self.write_file(items)
                    timeout = None
                    items = []

    def write_file(self, items):

        try:

            schema = pa.schema([
                pa.field('embeddings', pa.list_(pa.list_(pa.float64()))),
                pa.field('entity', pa.string()),
            ])

            fname = self.file_template.format(id=str(uuid.uuid4()))
            path = f"{self.directory}/{fname}"

            writer = pq.ParquetWriter(path, schema)

            batch = pa.record_batch(
                [
                    [i[0] for i in items],
                    [i[1] for i in items],
                ],
                names=['embeddings', 'entity']
            )

            writer.write_batch(batch)

            writer.close()

            print(f"Wrote {path}.")

        except Exception as e:

            print("Parquet write:", e)

    def write(self, embeds, ent):
        self.q.put((embeds, ent))

    def __del__(self):

        self.running = False

        if hasattr(self, "q"):
            self.thread.join()

            

        
