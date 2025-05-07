
from .. schema import KnowledgeResponse, Triple, Triples, EntityEmbeddings
from .. schema import Metadata, Value, GraphEmbeddings

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from ssl import SSLContext, PROTOCOL_TLSv1_2

import uuid
import time
import asyncio

class ConfigTableStore:

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

        print("config table...", flush=True)

        self.cassandra.execute("""
            CREATE TABLE IF NOT EXISTS config (
                class text,
                key text,
                value text,
                PRIMARY KEY (class, key)
            );
        """);

        print("Cassandra schema OK.", flush=True)

    def prepare_statements(self):

        self.put_config_stmt = self.cassandra.prepare("""
            INSERT INTO config ( class, key, value )
            VALUES (?, ?, ?)
        """)

        self.get_classes_stmt = self.cassandra.prepare("""
            SELECT DISTINCT class FROM config;
        """)

        self.get_keys_stmt = self.cassandra.prepare("""
            SELECT key FROM config WHERE class = ?;
        """)

        self.get_value_stmt = self.cassandra.prepare("""
            SELECT value FROM config WHERE class = ? AND key = ?;
        """)

        self.delete_key_stmt = self.cassandra.prepare("""
            DELETE FROM config
            WHERE class = ? AND key = ?;
        """)

        self.get_all_stmt = self.cassandra.prepare("""
            SELECT class, key, value FROM config;
        """)

        self.get_values_stmt = self.cassandra.prepare("""
            SELECT key, value FROM config WHERE class = ?;
        """)

    async def put_config(self, cls, key, value):

        while True:

            try:

                resp = self.cassandra.execute(
                    self.put_config_stmt,
                    ( cls, key, value )
                )

                break

            except Exception as e:

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)

    async def get_value(self, cls, key):

        while True:

            try:

                resp = self.cassandra.execute(
                    self.get_value_stmt,
                    ( cls, key )
                )

                break

            except Exception as e:

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)

        for row in resp:
            return row[0]

        return None

    async def get_values(self, cls):

        while True:

            try:

                resp = self.cassandra.execute(
                    self.get_values_stmt,
                    ( cls, )
                )

                break

            except Exception as e:

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)

        return [
            [row[0], row[1]]
            for row in resp
        ]

    async def get_classes(self):

        while True:

            try:

                resp = self.cassandra.execute(
                    self.get_classes_stmt,
                    ()
                )

                break

            except Exception as e:

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)

        return [
            row[0] for row in resp
        ]

    async def get_all(self):

        while True:

            try:

                resp = self.cassandra.execute(
                    self.get_all_stmt,
                    ()
                )

                break

            except Exception as e:

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)

        return [
            (row[0], row[1], row[2])
            for row in resp
        ]

    async def get_keys(self, cls):

        while True:

            try:

                resp = self.cassandra.execute(
                    self.get_keys_stmt,
                    ( cls, )
                )

                break

            except Exception as e:

                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)

        return [
            row[0] for row in resp
        ]

    async def delete_key(self, cls, key):

        while True:

            try:

                resp = self.cassandra.execute(
                    self.delete_key_stmt,
                    (cls, key)
                )

                break

            except Exception as e:
                print("Exception:", type(e))
                print(f"{e}, retry...", flush=True)
                await asyncio.sleep(1)

