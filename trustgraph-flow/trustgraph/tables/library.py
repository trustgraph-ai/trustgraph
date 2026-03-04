
from .. schema import LibrarianRequest, LibrarianResponse
from .. schema import DocumentMetadata, ProcessingMetadata
from .. schema import Error, Triple, Term, IRI, LITERAL
from .. knowledge import hash


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

        # Add parent_id and document_type columns for child document support
        logger.debug("document table parent_id column...")

        try:
            self.cassandra.execute("""
                ALTER TABLE document ADD parent_id text
            """);
        except Exception as e:
            # Column may already exist
            if "already exists" not in str(e).lower() and "Invalid column name" not in str(e):
                logger.debug(f"parent_id column may already exist: {e}")

        try:
            self.cassandra.execute("""
                ALTER TABLE document ADD document_type text
            """);
        except Exception as e:
            # Column may already exist
            if "already exists" not in str(e).lower() and "Invalid column name" not in str(e):
                logger.debug(f"document_type column may already exist: {e}")

        logger.debug("document parent index...")

        self.cassandra.execute("""
            CREATE INDEX IF NOT EXISTS document_parent
            ON document (parent_id)
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

        logger.debug("upload_session table...")

        self.cassandra.execute("""
            CREATE TABLE IF NOT EXISTS upload_session (
                upload_id text PRIMARY KEY,
                user text,
                document_id text,
                document_metadata text,
                s3_upload_id text,
                object_id uuid,
                total_size bigint,
                chunk_size int,
                total_chunks int,
                chunks_received map<int, text>,
                created_at timestamp,
                updated_at timestamp
            ) WITH default_time_to_live = 86400;
        """);

        logger.debug("upload_session user index...")

        self.cassandra.execute("""
            CREATE INDEX IF NOT EXISTS upload_session_user
            ON upload_session (user)
        """);

        logger.info("Cassandra schema OK.")

    def prepare_statements(self):

        self.insert_document_stmt = self.cassandra.prepare("""
            INSERT INTO document
            (
                id, user, time,
                kind, title, comments,
                metadata, tags, object_id,
                parent_id, document_type
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)

        self.update_document_stmt = self.cassandra.prepare("""
            UPDATE document
            SET time = ?, title = ?, comments = ?,
                metadata = ?, tags = ?
            WHERE user = ? AND id = ?
        """)

        self.get_document_stmt = self.cassandra.prepare("""
            SELECT time, kind, title, comments, metadata, tags, object_id,
                   parent_id, document_type
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
                id, time, kind, title, comments, metadata, tags, object_id,
                parent_id, document_type
            FROM document
            WHERE user = ?
        """)

        self.list_document_by_tag_stmt = self.cassandra.prepare("""
            SELECT
                id, time, kind, title, comments, metadata, tags, object_id,
                parent_id, document_type
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

        # Upload session prepared statements
        self.insert_upload_session_stmt = self.cassandra.prepare("""
            INSERT INTO upload_session
            (
                upload_id, user, document_id, document_metadata,
                s3_upload_id, object_id, total_size, chunk_size,
                total_chunks, chunks_received, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)

        self.get_upload_session_stmt = self.cassandra.prepare("""
            SELECT
                upload_id, user, document_id, document_metadata,
                s3_upload_id, object_id, total_size, chunk_size,
                total_chunks, chunks_received, created_at, updated_at
            FROM upload_session
            WHERE upload_id = ?
        """)

        self.update_upload_session_chunk_stmt = self.cassandra.prepare("""
            UPDATE upload_session
            SET chunks_received = chunks_received + ?,
                updated_at = ?
            WHERE upload_id = ?
        """)

        self.delete_upload_session_stmt = self.cassandra.prepare("""
            DELETE FROM upload_session
            WHERE upload_id = ?
        """)

        self.list_upload_sessions_stmt = self.cassandra.prepare("""
            SELECT
                upload_id, document_id, document_metadata,
                total_size, chunk_size, total_chunks,
                chunks_received, created_at, updated_at
            FROM upload_session
            WHERE user = ?
        """)

        # Child document queries
        self.list_children_stmt = self.cassandra.prepare("""
            SELECT
                id, user, time, kind, title, comments, metadata, tags,
                object_id, parent_id, document_type
            FROM document
            WHERE parent_id = ?
            ALLOW FILTERING
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
                *term_to_tuple(v.s), *term_to_tuple(v.p), *term_to_tuple(v.o)
            )
            for v in document.metadata
        ]

        # Get parent_id and document_type from document, defaulting if not set
        parent_id = getattr(document, 'parent_id', '') or ''
        document_type = getattr(document, 'document_type', 'source') or 'source'

        while True:

            try:

                resp = self.cassandra.execute(
                    self.insert_document_stmt,
                    (
                        document.id, document.user, int(document.time * 1000),
                        document.kind, document.title, document.comments,
                        metadata, document.tags, object_id,
                        parent_id, document_type
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
                *term_to_tuple(v.s), *term_to_tuple(v.p), *term_to_tuple(v.o)
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
                        s=tuple_to_term(m[0], m[1]),
                        p=tuple_to_term(m[2], m[3]),
                        o=tuple_to_term(m[4], m[5])
                    )
                    for m in row[5]
                ],
                tags = row[6] if row[6] else [],
                parent_id = row[8] if row[8] else "",
                document_type = row[9] if row[9] else "source",
            )
            for row in resp
        ]

        logger.debug("Done")

        return lst

    async def list_children(self, parent_id):
        """List all child documents for a given parent document ID."""

        logger.debug(f"List children for parent {parent_id}")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.list_children_stmt,
                    (parent_id,)
                )

                break

            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e

        lst = [
            DocumentMetadata(
                id = row[0],
                user = row[1],
                time = int(time.mktime(row[2].timetuple())),
                kind = row[3],
                title = row[4],
                comments = row[5],
                metadata = [
                    Triple(
                        s=tuple_to_term(m[0], m[1]),
                        p=tuple_to_term(m[2], m[3]),
                        o=tuple_to_term(m[4], m[5])
                    )
                    for m in row[6]
                ],
                tags = row[7] if row[7] else [],
                parent_id = row[9] if row[9] else "",
                document_type = row[10] if row[10] else "source",
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
                        s=tuple_to_term(m[0], m[1]),
                        p=tuple_to_term(m[2], m[3]),
                        o=tuple_to_term(m[4], m[5])
                    )
                    for m in row[4]
                ],
                tags = row[5] if row[5] else [],
                parent_id = row[7] if row[7] else "",
                document_type = row[8] if row[8] else "source",
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

    # Upload session methods

    async def create_upload_session(
        self,
        upload_id,
        user,
        document_id,
        document_metadata,
        s3_upload_id,
        object_id,
        total_size,
        chunk_size,
        total_chunks,
    ):
        """Create a new upload session for chunked upload."""

        logger.info(f"Creating upload session {upload_id}")

        now = int(time.time() * 1000)

        while True:
            try:
                self.cassandra.execute(
                    self.insert_upload_session_stmt,
                    (
                        upload_id, user, document_id, document_metadata,
                        s3_upload_id, object_id, total_size, chunk_size,
                        total_chunks, {}, now, now
                    )
                )
                break
            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e

        logger.debug("Upload session created")

    async def get_upload_session(self, upload_id):
        """Get an upload session by ID."""

        logger.debug(f"Get upload session {upload_id}")

        while True:
            try:
                resp = self.cassandra.execute(
                    self.get_upload_session_stmt,
                    (upload_id,)
                )
                break
            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e

        for row in resp:
            session = {
                "upload_id": row[0],
                "user": row[1],
                "document_id": row[2],
                "document_metadata": row[3],
                "s3_upload_id": row[4],
                "object_id": row[5],
                "total_size": row[6],
                "chunk_size": row[7],
                "total_chunks": row[8],
                "chunks_received": row[9] if row[9] else {},
                "created_at": row[10],
                "updated_at": row[11],
            }
            logger.debug("Done")
            return session

        return None

    async def update_upload_session_chunk(self, upload_id, chunk_index, etag):
        """Record a successfully uploaded chunk."""

        logger.debug(f"Update upload session {upload_id} chunk {chunk_index}")

        now = int(time.time() * 1000)

        while True:
            try:
                self.cassandra.execute(
                    self.update_upload_session_chunk_stmt,
                    (
                        {chunk_index: etag},
                        now,
                        upload_id
                    )
                )
                break
            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e

        logger.debug("Chunk recorded")

    async def delete_upload_session(self, upload_id):
        """Delete an upload session."""

        logger.info(f"Deleting upload session {upload_id}")

        while True:
            try:
                self.cassandra.execute(
                    self.delete_upload_session_stmt,
                    (upload_id,)
                )
                break
            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e

        logger.debug("Upload session deleted")

    async def list_upload_sessions(self, user):
        """List all upload sessions for a user."""

        logger.debug(f"List upload sessions for {user}")

        while True:
            try:
                resp = self.cassandra.execute(
                    self.list_upload_sessions_stmt,
                    (user,)
                )
                break
            except Exception as e:
                logger.error("Exception occurred", exc_info=True)
                raise e

        sessions = []
        for row in resp:
            chunks_received = row[6] if row[6] else {}
            sessions.append({
                "upload_id": row[0],
                "document_id": row[1],
                "document_metadata": row[2],
                "total_size": row[3],
                "chunk_size": row[4],
                "total_chunks": row[5],
                "chunks_received": len(chunks_received),
                "created_at": row[7],
                "updated_at": row[8],
            })

        logger.debug("Done")
        return sessions
