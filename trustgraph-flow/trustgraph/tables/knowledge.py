
from .. schema import KnowledgeResponse, Triple, Triples, EntityEmbeddings
from .. schema import Metadata, Term, IRI, LITERAL, GraphEmbeddings

from cassandra.cluster import Cluster


def term_to_tuple(term):
    """Convert Term to (value, is_uri) tuple for database storage."""
    if term.type == IRI:
        return (term.iri, True)
    else:  # LITERAL
        return (term.value, False)


def tuple_to_term(value, is_uri):
    """Convert (value, is_uri) tuple from database to Term."""
    if is_uri:
        return Term(type=IRI, iri=value)
    else:
        return Term(type=LITERAL, value=value)
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
            cassandra_host, cassandra_username, cassandra_password, keyspace,
    ):

        self.keyspace = keyspace

        logger.info("Connecting to Cassandra...")

        # Ensure cassandra_host is a list
        if isinstance(cassandra_host, str):
            cassandra_host = [h.strip() for h in cassandra_host.split(',')]

        if cassandra_username and cassandra_password:
            ssl_context = SSLContext(PROTOCOL_TLSv1_2)
            auth_provider = PlainTextAuthProvider(
                username=cassandra_username, password=cassandra_password
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
                    *term_to_tuple(v.s), *term_to_tuple(v.p), *term_to_tuple(v.o)
                )
                for v in m.metadata.metadata
            ]
        else:
            metadata = []

        triples = [
            (
                *term_to_tuple(v.s), *term_to_tuple(v.p), *term_to_tuple(v.o)
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
                    *term_to_tuple(v.s), *term_to_tuple(v.p), *term_to_tuple(v.o)
                )
                for v in m.metadata.metadata
            ]
        else:
            metadata = []

        entities = [
            (
                term_to_tuple(v.entity),
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
                    *term_to_tuple(v.s), *term_to_tuple(v.p), *term_to_tuple(v.o)
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
                        s = tuple_to_term(elt[0], elt[1]),
                        p = tuple_to_term(elt[2], elt[3]),
                        o = tuple_to_term(elt[4], elt[5]),
                    )
                    for elt in row[2]
                ]
            else:
                metadata = []

            triples = [
                Triple(
                    s = tuple_to_term(elt[0], elt[1]),
                    p = tuple_to_term(elt[2], elt[3]),
                    o = tuple_to_term(elt[4], elt[5]),
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
                        s = tuple_to_term(elt[0], elt[1]),
                        p = tuple_to_term(elt[2], elt[3]),
                        o = tuple_to_term(elt[4], elt[5]),
                    )
                    for elt in row[2]
                ]
            else:
                metadata = []

            entities = [
                EntityEmbeddings(
                    entity = tuple_to_term(ent[0][0], ent[0][1]),
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

