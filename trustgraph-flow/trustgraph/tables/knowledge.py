
from .. schema import KnowledgeResponse, Triple, Triples, EntityEmbeddings
from .. schema import Metadata, Value, GraphEmbeddings

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from ssl import SSLContext, PROTOCOL_TLSv1_2

import uuid
import time
import asyncio
import logging

logger = logging.getLogger(__name__)

class KnowledgeTableStore:

    def __init__(
            self,
            cassandra_host, cassandra_user, cassandra_password, keyspace,
    ):

        self.keyspace = keyspace

        logger.info("Connecting to Cassandra...")

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
        
        logger.info("Connected.")

        self.ensure_cassandra_schema()

        self.prepare_statements()

    def ensure_cassandra_schema(self):

        logger.debug("Ensure Cassandra schema...")

        logger.debug("Keyspace...")
        
        # FIXME: Replication factor should be configurable
        self.cassandra.execute(f"""
            create keyspace if not exists {self.keyspace}
                with replication = {{ 
                   'class' : 'SimpleStrategy', 
                   'replication_factor' : 1 
                }};
        """);

        self.cassandra.set_keyspace(self.keyspace)

        logger.debug("triples table...")

        self.cassandra.execute("""
            CREATE TABLE IF NOT EXISTS triples (
                user text,
                document_id text,
                id uuid,
                time timestamp,
                metadata list<tuple<
                    text, boolean, text, boolean, text, boolean
                >>,
                triples list<tuple<
                    text, boolean, text, boolean, text, boolean
                >>,
                PRIMARY KEY ((user, document_id), id)
            );
        """);

        logger.debug("graph_embeddings table...")

        self.cassandra.execute("""
            create table if not exists graph_embeddings (
                user text,
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
                PRIMARY KEY ((user, document_id), id)
            );
        """);

        self.cassandra.execute("""
            CREATE INDEX IF NOT EXISTS graph_embeddings_user ON
            graph_embeddings ( user );
        """);

        logger.debug("document_embeddings table...")

        self.cassandra.execute("""
            create table if not exists document_embeddings (
                user text,
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
                PRIMARY KEY ((user, document_id), id)
            );
        """);

        self.cassandra.execute("""
            CREATE INDEX IF NOT EXISTS document_embeddings_user ON
            document_embeddings ( user );
        """);

        logger.info("Cassandra schema OK.")

    def prepare_statements(self):

        self.insert_triples_stmt = self.cassandra.prepare("""
            INSERT INTO triples
            (
                id, user, document_id,
                time, metadata, triples
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """)

        self.insert_graph_embeddings_stmt = self.cassandra.prepare("""
            INSERT INTO graph_embeddings
            (
                id, user, document_id, time, metadata, entity_embeddings
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """)

        self.insert_document_embeddings_stmt = self.cassandra.prepare("""
            INSERT INTO document_embeddings
            (
                id, user, document_id, time, metadata, chunks
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """)

        self.list_cores_stmt = self.cassandra.prepare("""
            SELECT DISTINCT user, document_id FROM graph_embeddings
            WHERE user = ?
        """)

        self.get_triples_stmt = self.cassandra.prepare("""
            SELECT id, time, metadata, triples
            FROM triples
            WHERE user = ? AND document_id = ?
        """)

        self.get_graph_embeddings_stmt = self.cassandra.prepare("""
            SELECT id, time, metadata, entity_embeddings
            FROM graph_embeddings
            WHERE user = ? AND document_id = ?
        """)

        self.get_document_embeddings_stmt = self.cassandra.prepare("""
            SELECT id, time, metadata, chunks
            FROM document_embeddings
            WHERE user = ? AND document_id = ?
        """)

        self.delete_triples_stmt = self.cassandra.prepare("""
            DELETE FROM triples
            WHERE user = ? AND document_id = ?
        """)

        self.delete_graph_embeddings_stmt = self.cassandra.prepare("""
            DELETE FROM graph_embeddings
            WHERE user = ? AND document_id = ?
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
                        m.metadata.id, when,
                        metadata, triples,
                    )
                )

                break

            except Exception as e:

                logger.error("Exception occurred", exc_info=True)
                raise e

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
                        m.metadata.id, when,
                        metadata, entities,
                    )
                )

                break

            except Exception as e:

                logger.error("Exception occurred", exc_info=True)
                raise e

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
                        m.metadata.id, when,
                        metadata, chunks,
                    )
                )

                break

            except Exception as e:

                logger.error("Exception occurred", exc_info=True)
                raise e

    async def list_kg_cores(self, user):

        logger.debug("List kg cores...")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.list_cores_stmt,
                    (user,)
                )

                break

            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e


        lst = [
            row[1]
            for row in resp
        ]

        logger.debug("Done")

        return lst

    async def delete_kg_core(self, user, document_id):

        logger.debug("Delete kg cores...")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.delete_triples_stmt,
                    (user, document_id)
                )

                break

            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e

        while True:

            try:

                resp = self.cassandra.execute(
                    self.delete_graph_embeddings_stmt,
                    (user, document_id)
                )

                break

            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e

    async def get_triples(self, user, document_id, receiver):

        logger.debug("Get triples...")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.get_triples_stmt,
                    (user, document_id)
                )

                break

            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e

        for row in resp:

            if row[2]:
                metadata = [
                    Triple(
                        s = Value(value = elt[0], is_uri = elt[1]),
                        p = Value(value = elt[2], is_uri = elt[3]),
                        o = Value(value = elt[4], is_uri = elt[5]),
                    )
                    for elt in row[2]
                ]
            else:
                metadata = []

            triples = [
                Triple(
                    s = Value(value = elt[0], is_uri = elt[1]),
                    p = Value(value = elt[2], is_uri = elt[3]),
                    o = Value(value = elt[4], is_uri = elt[5]),
                )
                for elt in row[3]
            ]

            await receiver(
                Triples(
                    metadata = Metadata(
                        id = document_id,
                        user = user,
                        collection = "default",  # FIXME: What to put here?
                        metadata = metadata,
                    ),
                    triples = triples
                )
            )

        logger.debug("Done")

    async def get_graph_embeddings(self, user, document_id, receiver):

        logger.debug("Get GE...")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.get_graph_embeddings_stmt,
                    (user, document_id)
                )

                break

            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e

        for row in resp:

            if row[2]:
                metadata = [
                    Triple(
                        s = Value(value = elt[0], is_uri = elt[1]),
                        p = Value(value = elt[2], is_uri = elt[3]),
                        o = Value(value = elt[4], is_uri = elt[5]),
                    )
                    for elt in row[2]
                ]
            else:
                metadata = []

            entities = [
                EntityEmbeddings(
                    entity = Value(value = ent[0][0], is_uri = ent[0][1]),
                    vectors = ent[1]
                )
                for ent in row[3]
            ]

            await receiver(
                GraphEmbeddings(
                    metadata = Metadata(
                        id = document_id,
                        user = user,
                        collection = "default",   # FIXME: What to put here?
                        metadata = metadata,
                    ),
                    entities = entities
                )
            )                    

        logger.debug("Done")

