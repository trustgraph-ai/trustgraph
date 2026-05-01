
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

from . cassandra_async import async_execute

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
                workspace text,
                time timestamp,
                kind text,
                title text,
                comments text,
                metadata list<tuple<
                    text, boolean, text, boolean, text, boolean
                >>,
                tags list<text>,
                object_id uuid,
                parent_id text,
                document_type text,
                PRIMARY KEY (workspace, id)
            );
        """);

        logger.debug("object index...")

        self.cassandra.execute("""
            CREATE INDEX IF NOT EXISTS document_object
            ON document (object_id)
        """);

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
                workspace text,
                collection text,
                tags list<text>,
                PRIMARY KEY (workspace, id)
            );
        """);

        logger.debug("upload_session table...")

        self.cassandra.execute("""
            CREATE TABLE IF NOT EXISTS upload_session (
                upload_id text PRIMARY KEY,
                workspace text,
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

        logger.debug("upload_session workspace index...")

        self.cassandra.execute("""
            CREATE INDEX IF NOT EXISTS upload_session_workspace
            ON upload_session (workspace)
        """);

        logger.info("Cassandra schema OK.")

    def prepare_statements(self):

        self.insert_document_stmt = self.cassandra.prepare("""
            INSERT INTO document
            (
                id, workspace, time,
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
            WHERE workspace = ? AND id = ?
        """)

        self.get_document_stmt = self.cassandra.prepare("""
            SELECT time, kind, title, comments, metadata, tags, object_id,
                   parent_id, document_type
            FROM document
            WHERE workspace = ? AND id = ?
        """)

        self.delete_document_stmt = self.cassandra.prepare("""
            DELETE FROM document
            WHERE workspace = ? AND id = ?
        """)

        self.test_document_exists_stmt = self.cassandra.prepare("""
            SELECT id
            FROM document
            WHERE workspace = ? AND id = ?
            LIMIT 1
        """)

        self.list_document_stmt = self.cassandra.prepare("""
            SELECT
                id, time, kind, title, comments, metadata, tags, object_id,
                parent_id, document_type
            FROM document
            WHERE workspace = ?
        """)

        self.list_document_by_tag_stmt = self.cassandra.prepare("""
            SELECT
                id, time, kind, title, comments, metadata, tags, object_id,
                parent_id, document_type
            FROM document
            WHERE workspace = ? AND tags CONTAINS ?
            ALLOW FILTERING
        """)

        self.insert_processing_stmt = self.cassandra.prepare("""
            INSERT INTO processing
            (
                id, document_id, time,
                flow, workspace, collection,
                tags
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """)

        self.delete_processing_stmt = self.cassandra.prepare("""
            DELETE FROM processing
            WHERE workspace = ? AND id = ?
        """)

        self.test_processing_exists_stmt = self.cassandra.prepare("""
            SELECT id
            FROM processing
            WHERE workspace = ? AND id = ?
            LIMIT 1
        """)

        self.list_processing_stmt = self.cassandra.prepare("""
            SELECT
                id, document_id, time, flow, collection, tags
            FROM processing
            WHERE workspace = ?
        """)

        # Upload session prepared statements
        self.insert_upload_session_stmt = self.cassandra.prepare("""
            INSERT INTO upload_session
            (
                upload_id, workspace, document_id, document_metadata,
                s3_upload_id, object_id, total_size, chunk_size,
                total_chunks, chunks_received, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)

        self.get_upload_session_stmt = self.cassandra.prepare("""
            SELECT
                upload_id, workspace, document_id, document_metadata,
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
            WHERE workspace = ?
        """)

        # Child document queries
        self.list_children_stmt = self.cassandra.prepare("""
            SELECT
                id, workspace, time, kind, title, comments, metadata, tags,
                object_id, parent_id, document_type
            FROM document
            WHERE parent_id = ?
            ALLOW FILTERING
        """)

    async def document_exists(self, workspace, id):

        rows = await async_execute(
            self.cassandra,
            self.test_document_exists_stmt,
            (workspace, id),
        )

        return bool(rows)

    async def add_document(self, workspace, document, object_id):

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

        try:
            await async_execute(
                self.cassandra,
                self.insert_document_stmt,
                (
                    document.id, workspace, int(document.time * 1000),
                    document.kind, document.title, document.comments,
                    metadata, document.tags, object_id,
                    parent_id, document_type
                ),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        logger.debug("Add complete")

    async def update_document(self, workspace, document):

        logger.info(f"Updating document {document.id}")

        metadata = [
            (
                *term_to_tuple(v.s), *term_to_tuple(v.p), *term_to_tuple(v.o)
            )
            for v in document.metadata
        ]

        try:
            await async_execute(
                self.cassandra,
                self.update_document_stmt,
                (
                    int(document.time * 1000), document.title,
                    document.comments, metadata, document.tags,
                    workspace, document.id
                ),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        logger.debug("Update complete")

    async def remove_document(self, workspace, document_id):

        logger.info(f"Removing document {document_id}")

        try:
            await async_execute(
                self.cassandra,
                self.delete_document_stmt,
                (workspace, document_id),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        logger.debug("Delete complete")

    async def list_documents(self, workspace):

        logger.debug("List documents...")

        try:
            rows = await async_execute(
                self.cassandra,
                self.list_document_stmt,
                (workspace,),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        lst = [
            DocumentMetadata(
                id = row[0],
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
                    for m in (row[5] or [])
                ],
                tags = row[6] if row[6] else [],
                parent_id = row[8] if row[8] else "",
                document_type = row[9] if row[9] else "source",
            )
            for row in rows
        ]

        logger.debug("Done")

        return lst

    async def list_children(self, parent_id):
        """List all child documents for a given parent document ID."""

        logger.debug(f"List children for parent {parent_id}")

        try:
            rows = await async_execute(
                self.cassandra,
                self.list_children_stmt,
                (parent_id,),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        lst = [
            DocumentMetadata(
                id = row[0],
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
                    for m in (row[6] or [])
                ],
                tags = row[7] if row[7] else [],
                parent_id = row[9] if row[9] else "",
                document_type = row[10] if row[10] else "source",
            )
            for row in rows
        ]

        logger.debug("Done")

        return lst

    async def get_document(self, workspace, id):

        logger.debug("Get document")

        try:
            rows = await async_execute(
                self.cassandra,
                self.get_document_stmt,
                (workspace, id),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        for row in rows:
            doc = DocumentMetadata(
                id = id,
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
                    for m in (row[4] or [])
                ],
                tags = row[5] if row[5] else [],
                parent_id = row[7] if row[7] else "",
                document_type = row[8] if row[8] else "source",
            )

            logger.debug("Done")
            return doc

        raise RuntimeError("No such document row?")

    async def get_document_object_id(self, workspace, id):

        logger.debug("Get document obj ID")

        try:
            rows = await async_execute(
                self.cassandra,
                self.get_document_stmt,
                (workspace, id),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        for row in rows:
            logger.debug("Done")
            return row[6]

        raise RuntimeError("No such document row?")

    async def processing_exists(self, workspace, id):

        rows = await async_execute(
            self.cassandra,
            self.test_processing_exists_stmt,
            (workspace, id),
        )

        return bool(rows)

    async def add_processing(self, workspace, processing):

        logger.info(f"Adding processing {processing.id}")

        try:
            await async_execute(
                self.cassandra,
                self.insert_processing_stmt,
                (
                    processing.id, processing.document_id,
                    int(processing.time * 1000), processing.flow,
                    workspace, processing.collection,
                    processing.tags
                ),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        logger.debug("Add complete")

    async def remove_processing(self, workspace, processing_id):

        logger.info(f"Removing processing {processing_id}")

        try:
            await async_execute(
                self.cassandra,
                self.delete_processing_stmt,
                (workspace, processing_id),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        logger.debug("Delete complete")

    async def list_processing(self, workspace):

        logger.debug("List processing objects")

        try:
            rows = await async_execute(
                self.cassandra,
                self.list_processing_stmt,
                (workspace,),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        lst = [
            ProcessingMetadata(
                id = row[0],
                document_id = row[1],
                time = int(time.mktime(row[2].timetuple())),
                flow = row[3],
                collection = row[4],
                tags = row[5] if row[5] else [],
            )
            for row in rows
        ]

        logger.debug("Done")

        return lst

    # Upload session methods

    async def create_upload_session(
        self,
        upload_id,
        workspace,
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

        try:
            await async_execute(
                self.cassandra,
                self.insert_upload_session_stmt,
                (
                    upload_id, workspace, document_id, document_metadata,
                    s3_upload_id, object_id, total_size, chunk_size,
                    total_chunks, {}, now, now
                ),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        logger.debug("Upload session created")

    async def get_upload_session(self, upload_id):
        """Get an upload session by ID."""

        logger.debug(f"Get upload session {upload_id}")

        try:
            rows = await async_execute(
                self.cassandra,
                self.get_upload_session_stmt,
                (upload_id,),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        for row in rows:
            session = {
                "upload_id": row[0],
                "workspace": row[1],
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

        try:
            await async_execute(
                self.cassandra,
                self.update_upload_session_chunk_stmt,
                (
                    {chunk_index: etag},
                    now,
                    upload_id
                ),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        logger.debug("Chunk recorded")

    async def delete_upload_session(self, upload_id):
        """Delete an upload session."""

        logger.info(f"Deleting upload session {upload_id}")

        try:
            await async_execute(
                self.cassandra,
                self.delete_upload_session_stmt,
                (upload_id,),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        logger.debug("Upload session deleted")

    async def list_upload_sessions(self, workspace):
        """List all upload sessions for a workspace."""

        logger.debug(f"List upload sessions for {workspace}")

        try:
            rows = await async_execute(
                self.cassandra,
                self.list_upload_sessions_stmt,
                (workspace,),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        sessions = []
        for row in rows:
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
