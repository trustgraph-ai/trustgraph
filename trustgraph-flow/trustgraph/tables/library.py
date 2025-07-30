
from .. schema import LibrarianRequest, LibrarianResponse
from .. schema import DocumentMetadata, ProcessingMetadata
from .. schema import Error, Triple, Value
from .. knowledge import hash
from .. exceptions import RequestError

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import BatchStatement
from ssl import SSLContext, PROTOCOL_TLSv1_2

import uuid
import time
import asyncio
import logging

logger = logging.getLogger(__name__)

class LibraryTableStore:

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

        logger.debug("document table...")

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

        logger.debug("object index...")

        self.cassandra.execute("""
            CREATE INDEX IF NOT EXISTS document_object
            ON document (object_id)
        """);

        logger.debug("processing table...")

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

        logger.info("Cassandra schema OK.")

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

        self.update_document_stmt = self.cassandra.prepare("""
            UPDATE document
            SET time = ?, title = ?, comments = ?,
                metadata = ?, tags = ?
            WHERE user = ? AND id = ?
        """)

        self.get_document_stmt = self.cassandra.prepare("""
            SELECT time, kind, title, comments, metadata, tags, object_id
            FROM document
            WHERE user = ? AND id = ?
        """)

        self.delete_document_stmt = self.cassandra.prepare("""
            DELETE FROM document
            WHERE user = ? AND id = ?
        """)

        self.test_document_exists_stmt = self.cassandra.prepare("""
            SELECT id
            FROM document
            WHERE user = ? AND id = ?
            LIMIT 1
        """)

        self.list_document_stmt = self.cassandra.prepare("""
            SELECT
                id, time, kind, title, comments, metadata, tags, object_id
            FROM document
            WHERE user = ?
        """)

        self.list_document_by_tag_stmt = self.cassandra.prepare("""
            SELECT
                id, time, kind, title, comments, metadata, tags, object_id
            FROM document
            WHERE user = ? AND tags CONTAINS ?
            ALLOW FILTERING
        """)

        self.insert_processing_stmt = self.cassandra.prepare("""
            INSERT INTO processing
            (
                id, document_id, time,
                flow, user, collection,
                tags
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """)

        self.delete_processing_stmt = self.cassandra.prepare("""
            DELETE FROM processing
            WHERE user = ? AND id = ?
        """)

        self.test_processing_exists_stmt = self.cassandra.prepare("""
            SELECT id
            FROM processing
            WHERE user = ? AND id = ?
            LIMIT 1
        """)

        self.list_processing_stmt = self.cassandra.prepare("""
            SELECT
                id, document_id, time, flow, collection, tags
            FROM processing
            WHERE user = ?
        """)

    async def document_exists(self, user, id):

        resp = self.cassandra.execute(
            self.test_document_exists_stmt,
            ( user, id )
        )

        # If a row exists, document exists.  It's a cursor, can't just
        # count the length

        for row in resp:
            return True

        return False

    async def add_document(self, document, object_id):

        logger.info(f"Adding document {document.id} {object_id}")

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
                        document.id, document.user, int(document.time * 1000),
                        document.kind, document.title, document.comments,
                        metadata, document.tags, object_id
                    )
                )

                break

            except Exception as e:

                logger.error("Exception occurred", exc_info=True)
                raise e

        logger.debug("Add complete")

    async def update_document(self, document):

        logger.info(f"Updating document {document.id}")

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
                    self.update_document_stmt,
                    (
                        int(document.time * 1000), document.title,
                        document.comments, metadata, document.tags,
                        document.user, document.id
                    )
                )

                break

            except Exception as e:

                logger.error("Exception occurred", exc_info=True)
                raise e

        logger.debug("Update complete")

    async def remove_document(self, user, document_id):

        logger.info(f"Removing document {document_id}")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.delete_document_stmt,
                    (
                        user, document_id
                    )
                )

                break

            except Exception as e:

                logger.error("Exception occurred", exc_info=True)
                raise e

        logger.debug("Delete complete")

    async def list_documents(self, user):

        logger.debug("List documents...")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.list_document_stmt,
                    (user,)
                )

                break

            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e


        lst = [
            DocumentMetadata(
                id = row[0],
                user = user,
                time = int(time.mktime(row[1].timetuple())),
                kind = row[2],
                title = row[3],
                comments = row[4],
                metadata = [
                    Triple(
                        s=Value(value=m[0], is_uri=m[1]),
                        p=Value(value=m[2], is_uri=m[3]),
                        o=Value(value=m[4], is_uri=m[5])
                    )
                    for m in row[5]
                ],
                tags = row[6] if row[6] else [],
                object_id = row[7],
            )
            for row in resp
        ]

        logger.debug("Done")

        return lst

    async def get_document(self, user, id):

        logger.debug("Get document")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.get_document_stmt,
                    (user, id)
                )

                break

            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e


        for row in resp:
            doc = DocumentMetadata(
                id = id,
                user = user,
                time = int(time.mktime(row[0].timetuple())),
                kind = row[1],
                title = row[2],
                comments = row[3],
                metadata = [
                    Triple(
                        s=Value(value=m[0], is_uri=m[1]),
                        p=Value(value=m[2], is_uri=m[3]),
                        o=Value(value=m[4], is_uri=m[5])
                    )
                    for m in row[4]
                ],
                tags = row[5] if row[5] else [],
                object_id = row[6],
            )

            logger.debug("Done")
            return doc

        raise RuntimeError("No such document row?")

    async def get_document_object_id(self, user, id):

        logger.debug("Get document obj ID")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.get_document_stmt,
                    (user, id)
                )

                break

            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e


        for row in resp:
            logger.debug("Done")
            return row[6]

        raise RuntimeError("No such document row?")

    async def processing_exists(self, user, id):

        resp = self.cassandra.execute(
            self.test_processing_exists_stmt,
            ( user, id )
        )

        # If a row exists, document exists.  It's a cursor, can't just
        # count the length

        for row in resp:
            return True

        return False

    async def add_processing(self, processing):

        logger.info(f"Adding processing {processing.id}")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.insert_processing_stmt,
                    (
                        processing.id, processing.document_id,
                        int(processing.time * 1000), processing.flow,
                        processing.user, processing.collection,
                        processing.tags
                    )
                )

                break

            except Exception as e:

                logger.error("Exception occurred", exc_info=True)
                raise e

        logger.debug("Add complete")

    async def remove_processing(self, user, processing_id):

        logger.info(f"Removing processing {processing_id}")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.delete_processing_stmt,
                    (
                        user, processing_id
                    )
                )

                break

            except Exception as e:

                logger.error("Exception occurred", exc_info=True)
                raise e

        logger.debug("Delete complete")

    async def list_processing(self, user):

        logger.debug("List processing objects")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.list_processing_stmt,
                    (user,)
                )

                break

            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e


        lst = [
            ProcessingMetadata(
                id = row[0],
                document_id = row[1],
                time = int(time.mktime(row[2].timetuple())),
                flow = row[3],
                user = user,
                collection = row[4],
                tags = row[5] if row[5] else [],
            )
            for row in resp
        ]

        logger.debug("Done")

        return lst

