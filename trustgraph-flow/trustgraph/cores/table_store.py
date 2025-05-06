
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from ssl import SSLContext, PROTOCOL_TLSv1_2

import uuid
import time
import asyncio

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

    async def add_triples(self, m):

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
                await asyncio.sleep(1)

    async def add_graph_embeddings(self, m):

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
                await asyncio.sleep(1)

    async def add_document_embeddings(self, m):

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
                await asyncio.sleep(1)

        
