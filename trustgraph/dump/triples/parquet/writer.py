
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

        triples = []

        timeout = None

        while self.running:

            try:

                item = self.q.get(timeout=1)

                if timeout == None:
                    timeout = time.time() + self.rotation_time

                triples.append(item)

            except queue.Empty:
                pass

            if timeout:
                if time.time() > timeout:

                    self.write_file(triples)
                    timeout = None
                    triples = []

    def write_file(self, triples):

        try:

            schema = pa.schema([
                pa.field('s', pa.string()),
                pa.field('p', pa.string()),
                pa.field('o', pa.string()),
            ])

            fname = self.file_template.format(id=str(uuid.uuid4()))
            path = f"{self.directory}/{fname}"

            writer = pq.ParquetWriter(path, schema)

            batch = pa.record_batch(
                [
                    [tpl[0] for tpl in triples],
                    [tpl[1] for tpl in triples],
                    [tpl[2] for tpl in triples],
                ],
                names=['s', 'p', 'o']
            )

            writer.write_batch(batch)

            writer.close()

            print(f"Wrote {path}.")

        except Exception as e:

            print("Parquet write:", e)

    def write(self, s, p, o):
        self.q.put((s, p, o))

    def __del__(self):

        self.running = False

        if hasattr(self, "q"):
            self.thread.join()

            

        
