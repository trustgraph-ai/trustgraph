from .. schema import LibrarianRequest, LibrarianResponse, Error
from .. knowledge import hash
from .. exceptions import RequestError

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import BatchStatement
import uuid
import time

class TableStore:

    def __init__(
            self,
            cassandra_host, cassandra_user, cassandra_password, keyspace,
    ):

        self.keyspace = keyspace

        print("Connecting to Cassandra...", flush=True)

        if cassandra_user and cassandra_password:
            auth_provider = PlainTextAuthProvider(
                username=cassandra_user, password=cassandra_password
            )
            self.cluster = Cluster(
                cassandra_host,
                auth_provider=auth_provider
            )
        else:
            self.cluster = Cluster(cassandra_host)

        self.cassandra = self.cluster.connect()
        
        print("Connected.", flush=True)

        self.ensure_cassandra_schema()

        self.insert_document_stmt = self.cassandra.prepare("""
            insert into document
            (id, user, collection, kind, object_id, metadata)
            values (?, ?, ?, ?, ?, ?)
        """)

    def ensure_cassandra_schema(self):

        print("Ensure Cassandra schema...", flush=True)

        print("Keyspace...", flush=True)
        
        # FIXME: Replication factor should be configurable
        self.cassandra.execute(f"""
            create keyspace if not exists {self.keyspace}
                with replication = {{ 
                   'class' : 'SimpleStrategy', 
                   'replication_factor' : 1 
                }};
        """);

        self.cassandra.set_keyspace(self.keyspace)

        print("document table...", flush=True)

        self.cassandra.execute("""
            create table if not exists document (
                user text,
                collection text,
                id uuid,
                kind text,
                object_id uuid,
                metadata list<tuple<
                    text, boolean, text, boolean, text, boolean
                >>,
                PRIMARY KEY (user, collection, id)
            );
        """);

        print("object index...", flush=True)

        self.cassandra.execute("""
            create index if not exists document_object
            on document ( object_id)
        """);

        print("Cassandra schema OK.", flush=True)

    def add(self, object_id, document):

        if document.kind not in (
                "text/plain", "application/pdf"
        ):
            raise RequestError("Invalid document kind: " + document.kind)

        # Create random doc ID
        doc_id = uuid.uuid4()

        print("Adding", object_id, doc_id)

        metadata = [
            (
                v.s.value, v.s.is_uri, v.p.value, v.p.is_uri,
                v.o.value, v.o.is_uri
            )
            for v in document.metadata
        ]

        while True:

            try:

                resp = self.cassandra.execute(
                    self.insert_document_stmt,
                    (
                        doc_id, document.user, document.collection, 
                        document.kind, object_id, metadata
                    )
                )

                break

            except Exception as e:

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                time.sleep(1)

        print("Add complete", flush=True)




