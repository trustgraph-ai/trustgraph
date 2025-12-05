
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

        # Collection management statements
        self.insert_collection_stmt = self.cassandra.prepare("""
            INSERT INTO collections
            (user, collection, name, description, tags, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
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



    # Collection management methods

    async def ensure_collection_exists(self, user, collection):
        """Ensure collection metadata record exists, create if not"""
        try:
            resp = await asyncio.get_event_loop().run_in_executor(
                None, self.cassandra.execute, self.collection_exists_stmt, [user, collection]
            )
            if resp:
                return
            import datetime
            now = datetime.datetime.now()
            await asyncio.get_event_loop().run_in_executor(
                None, self.cassandra.execute, self.insert_collection_stmt,
                [user, collection, collection, "", set(), now, now]
            )
            logger.debug(f"Created collection metadata for {user}/{collection}")
        except Exception as e:
            logger.error(f"Error ensuring collection exists: {e}")
            raise

    async def list_collections(self, user, tag_filter=None):
        """List collections for a user, optionally filtered by tags"""
        try:
            resp = await asyncio.get_event_loop().run_in_executor(
                None, self.cassandra.execute, self.list_collections_stmt, [user]
            )
            collections = []
            for row in resp:
                collection_data = {
                    "user": user,
                    "collection": row[0],
                    "name": row[1] or row[0],
                    "description": row[2] or "",
                    "tags": list(row[3]) if row[3] else [],
                    "created_at": row[4].isoformat() if row[4] else "",
                    "updated_at": row[5].isoformat() if row[5] else ""
                }
                if tag_filter:
                    collection_tags = set(collection_data["tags"])
                    filter_tags = set(tag_filter)
                    if not filter_tags.intersection(collection_tags):
                        continue
                collections.append(collection_data)
            return collections
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            raise

    async def update_collection(self, user, collection, name=None, description=None, tags=None):
        """Update collection metadata"""
        try:
            resp = await asyncio.get_event_loop().run_in_executor(
                None, self.cassandra.execute, self.get_collection_stmt, [user, collection]
            )
            if not resp:
                raise RequestError(f"Collection {collection} not found")
            row = resp.one()
            current_name = row[1] or collection
            current_description = row[2] or ""
            current_tags = set(row[3]) if row[3] else set()
            new_name = name if name is not None else current_name
            new_description = description if description is not None else current_description
            new_tags = set(tags) if tags is not None else current_tags
            import datetime
            now = datetime.datetime.now()
            await asyncio.get_event_loop().run_in_executor(
                None, self.cassandra.execute, self.update_collection_stmt,
                [new_name, new_description, new_tags, now, user, collection]
            )
            return {
                "user": user, "collection": collection, "name": new_name,
                "description": new_description, "tags": list(new_tags),
                "updated_at": now.isoformat()
            }
        except Exception as e:
            logger.error(f"Error updating collection: {e}")
            raise

    async def delete_collection(self, user, collection):
        """Delete collection metadata record"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self.cassandra.execute, self.delete_collection_stmt, [user, collection]
            )
            logger.debug(f"Deleted collection metadata for {user}/{collection}")
        except Exception as e:
            logger.error(f"Error deleting collection metadata: {e}")
            raise

    async def get_collection(self, user, collection):
        """Get collection metadata"""
        try:
            resp = await asyncio.get_event_loop().run_in_executor(
                None, self.cassandra.execute, self.get_collection_stmt, [user, collection]
            )
            if not resp:
                return None
            row = resp.one()
            return {
                "user": user, "collection": row[0], "name": row[1] or row[0],
                "description": row[2] or "", "tags": list(row[3]) if row[3] else [],
                "created_at": row[4].isoformat() if row[4] else "",
                "updated_at": row[5].isoformat() if row[5] else ""
            }
        except Exception as e:
            logger.error(f"Error getting collection: {e}")
            raise

    async def create_collection(self, user, collection, name=None, description=None, tags=None):
        """Create a new collection metadata record"""
        try:
            import datetime
            now = datetime.datetime.now()

            # Set defaults for optional parameters
            name = name if name is not None else collection
            description = description if description is not None else ""
            tags = tags if tags is not None else set()

            await asyncio.get_event_loop().run_in_executor(
                None, self.cassandra.execute, self.insert_collection_stmt,
                [user, collection, name, description, tags, now, now]
            )

            logger.info(f"Created collection {user}/{collection}")

            # Return the created collection data
            return {
                "user": user,
                "collection": collection,
                "name": name,
                "description": description,
                "tags": list(tags) if isinstance(tags, set) else tags,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat()
            }
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise
