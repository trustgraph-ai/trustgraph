from .. schema import LibrarianRequest, LibrarianResponse
from .. schema import DocumentMetadata, Error, Triple, Value
from .. knowledge import hash
from .. exceptions import RequestError

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import BatchStatement
from ssl import SSLContext, PROTOCOL_TLSv1_2
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
            ssl_context = SSLContext(PROTOCOL_TLSv1_2)
            auth_provider = PlainTextAuthProvider(
                username=cassandra_user, password=cassandra_password
            )
            self.cluster = Cluster(
                cassandra_host,
                auth_provider=auth_provider,
                ssl_context=ssl_context
            )
        else:
            self.cluster = Cluster(cassandra_host)

        self.cassandra = self.cluster.connect()
        
        print("Connected.", flush=True)

        self.ensure_cassandra_schema()

        self.prepare_statements()

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
            CREATE TABLE IF NOT EXISTS document (
                id text,
                user text,
                time timestamp,
                kind text,
                title text,
                comments text,
                metadata list<tuple<
                    text, boolean, text, boolean, text, boolean
                >>,
                tags list<text>,
                object_id uuid,
                PRIMARY KEY (user, id)
            );
        """);

        print("object index...", flush=True)

        self.cassandra.execute("""
            CREATE INDEX IF NOT EXISTS document_object
            ON document (object_id)
        """);

        print("processing table...", flush=True)

        self.cassandra.execute("""
            CREATE TABLE IF NOT EXISTS processing (
                id text,
                document_id text,
                time timestamp,
                flow text,
                user text,
                collection text,
                tags list<text>,
                PRIMARY KEY (user, id)
            );
        """);

        return

        print("triples table...", flush=True)

        self.cassandra.execute("""
            CREATE TABLE IF NOT EXISTS triples (
                user text,
                collection text,
                document_id text,
                id uuid,
                time timestamp,
                metadata list<tuple<
                    text, boolean, text, boolean, text, boolean
                >>,
                triples list<tuple<
                    text, boolean, text, boolean, text, boolean
                >>,
                PRIMARY KEY (user, collection, document_id, id)
            );
        """);

        print("graph_embeddings table...", flush=True)

        self.cassandra.execute("""
            create table if not exists graph_embeddings (
                user text,
                collection text,
                document_id text,
                id uuid,
                time timestamp,
                metadata list<tuple<
                    text, boolean, text, boolean, text, boolean
                >>,
                entity_embeddings list<
                    tuple<
                        tuple<text, boolean>,
                        list<list<double>>
                    >
                >,
                PRIMARY KEY (user, collection, document_id, id)
            );
        """);

        print("document_embeddings table...", flush=True)

        self.cassandra.execute("""
            create table if not exists document_embeddings (
                user text,
                collection text,
                document_id text,
                id uuid,
                time timestamp,
                metadata list<tuple<
                    text, boolean, text, boolean, text, boolean
                >>,
                chunks list<
                    tuple<
                        blob,
                        list<list<double>>
                    >
                >,
                PRIMARY KEY (user, collection, document_id, id)
            );
        """);

        print("Cassandra schema OK.", flush=True)

    def prepare_statements(self):

        self.insert_document_stmt = self.cassandra.prepare("""
            INSERT INTO document
            (
                id, user, time,
                kind, title, comments,
                metadata, tags, object_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)

        self.list_document_stmt = self.cassandra.prepare("""
            SELECT
                id, time, kind, title, comments, metadata, tags, object_id
            FROM document
            WHERE user = ?
        """)

        self.list_document_by_collection_stmt = self.cassandra.prepare("""
            SELECT
                id, time, kind, title, comments, metadata, tags, object_id
            FROM document
            WHERE user = ? AND tags CONTAINS ?
            ALLOW FILTERING
        """)

        return

        self.insert_triples_stmt = self.cassandra.prepare("""
            INSERT INTO triples
            (
                id, user, collection, document_id, time,
                metadata, triples
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """)

        self.insert_graph_embeddings_stmt = self.cassandra.prepare("""
            INSERT INTO graph_embeddings
            (
                id, user, collection, document_id, time,
                metadata, entity_embeddings
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """)

        self.insert_document_embeddings_stmt = self.cassandra.prepare("""
            INSERT INTO document_embeddings
            (
                id, user, collection, document_id, time,
                metadata, chunks
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """)

    def add_document(self, document, object_id):

        # if document.kind not in (
        #         "text/plain", "application/pdf"
        # ):
        #     raise RequestError("Invalid document kind: " + document.kind)

        # Create timestamp
        when = int(time.time() * 1000)

        print("Adding document", document.id, object_id)

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
                        document.id, document.user, when,
                        document.kind, document.title, document.comments,
                        metadata, document.tags, object_id
                    )
                )

                break

            except Exception as e:

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                time.sleep(1)

        print("Add complete", flush=True)

    def add_triples(self, m):

        when = int(time.time() * 1000)

        if m.metadata.metadata:
            metadata = [
                (
                    v.s.value, v.s.is_uri, v.p.value, v.p.is_uri,
                    v.o.value, v.o.is_uri
                )
                for v in m.metadata.metadata
            ]
        else:
            metadata = []

        triples = [
            (
                v.s.value, v.s.is_uri, v.p.value, v.p.is_uri,
                v.o.value, v.o.is_uri
            )
            for v in m.triples
        ]

        while True:

            try:

                resp = self.cassandra.execute(
                    self.insert_triples_stmt,
                    (
                        uuid.uuid4(), m.metadata.user,
                        m.metadata.collection, m.metadata.id, when,
                        metadata, triples,
                    )
                )

                break

            except Exception as e:

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                time.sleep(1)

    def list(self, user, collection=None):

        print("LIST")
        while True:

            print("TRY")

            print(self.list_document_stmt)
            try:

                if collection:
                    resp = self.cassandra.execute(
                        self.list_document_by_collection_stmt,
                        (user, collection)
                    )
                else:
                    resp = self.cassandra.execute(
                        self.list_document_stmt,
                        (user,)
                    )
                break

                print("OK")

            except Exception as e:
                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                time.sleep(1)

        print("OK2")

        info = [
            DocumentMetadata(
                id = row[0],
                kind = row[1],
                flow = row[2],
                user = row[3],
                collection = row[4],
                title = row[5],
                comments = row[6],
                time = int(1000 * row[7].timestamp()),
                metadata = [
                    Triple(
                        s=Value(value=m[0], is_uri=m[1]),
                        p=Value(value=m[2], is_uri=m[3]),
                        o=Value(value=m[4], is_uri=m[5])
                    )
                    for m in row[8]
                ],
            )
            for row in resp
        ]

        print("OK3")

        print(info)

        # print(info[0].user)
        # print(info[0].time)
        # print(info[0].kind)
        # print(info[0].collection)
        # print(info[0].title)
        # print(info[0].comments)
        # print(info[0].metadata)
        # print(info[0].metadata)

        return info

    def add_graph_embeddings(self, m):

        when = int(time.time() * 1000)

        if m.metadata.metadata:
            metadata = [
                (
                    v.s.value, v.s.is_uri, v.p.value, v.p.is_uri,
                    v.o.value, v.o.is_uri
                )
                for v in m.metadata.metadata
            ]
        else:
            metadata = []

        entities = [
            (
                (v.entity.value, v.entity.is_uri),
                v.vectors
            )
            for v in m.entities
        ]

        while True:

            try:

                resp = self.cassandra.execute(
                    self.insert_graph_embeddings_stmt,
                    (
                        uuid.uuid4(), m.metadata.user,
                        m.metadata.collection, m.metadata.id, when,
                        metadata, entities,
                    )
                )

                break

            except Exception as e:

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                time.sleep(1)

    def add_document_embeddings(self, m):

        when = int(time.time() * 1000)

        if m.metadata.metadata:
            metadata = [
                (
                    v.s.value, v.s.is_uri, v.p.value, v.p.is_uri,
                    v.o.value, v.o.is_uri
                )
                for v in m.metadata.metadata
            ]
        else:
            metadata = []

        chunks = [
            (
                v.chunk,
                v.vectors,
            )
            for v in m.chunks
        ]

        while True:

            try:

                resp = self.cassandra.execute(
                    self.insert_document_embeddings_stmt,
                    (
                        uuid.uuid4(), m.metadata.user,
                        m.metadata.collection, m.metadata.id, when,
                        metadata, chunks,
                    )
                )

                break

            except Exception as e:

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                time.sleep(1)

        
