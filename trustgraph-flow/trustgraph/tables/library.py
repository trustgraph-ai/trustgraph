
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

class LibraryTableStore:

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
                        document.id, document.user, int(document.time * 1000),
                        document.kind, document.title, document.comments,
                        metadata, document.tags, object_id
                    )
                )

                break

            except Exception as e:

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)

        print("Add complete", flush=True)

    async def update_document(self, document):

        print("Updating document", document.id)

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

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)

        print("Update complete", flush=True)

    async def remove_document(self, user, document_id):

        print("Removing document", document_id)

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

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)

        print("Delete complete", flush=True)

    async def list_documents(self, user):

        print("List documents...")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.list_document_stmt,
                    (user,)
                )

                break

            except Exception as e:
                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)


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

        print("Done")

        return lst

    async def get_document(self, user, id):

        print("Get document")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.get_document_stmt,
                    (user, id)
                )

                break

            except Exception as e:
                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)


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

            print("Done")
            return doc

        raise RuntimeError("No such document row?")

    async def get_document_object_id(self, user, id):

        print("Get document obj ID")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.get_document_stmt,
                    (user, id)
                )

                break

            except Exception as e:
                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)


        for row in resp:
            print("Done")
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

        print("Adding processing", processing.id)

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

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)

        print("Add complete", flush=True)

    async def remove_processing(self, user, processing_id):

        print("Removing processing", processing_id)

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

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)

        print("Delete complete", flush=True)

    async def list_processing(self, user):

        print("List processing objects")

        while True:

            try:

                resp = self.cassandra.execute(
                    self.list_processing_stmt,
                    (user,)
                )

                break

            except Exception as e:
                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)


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

        print("Done")

        return lst

