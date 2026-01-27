
from .. schema import KnowledgeResponse, Triple, Triples, EntityEmbeddings
from .. schema import Metadata, GraphEmbeddings

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from ssl import SSLContext, PROTOCOL_TLSv1_2

import uuid
import time
import asyncio
import logging

logger = logging.getLogger(__name__)

class ConfigTableStore:

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

        logger.debug("config table...")

        self.cassandra.execute("""
            CREATE TABLE IF NOT EXISTS config (
                class text,
                key text,
                value text,
                PRIMARY KEY (class, key)
            );
        """);

        logger.debug("version table...")

        self.cassandra.execute("""
            CREATE TABLE IF NOT EXISTS version (
                id text,
                version counter,
                PRIMARY KEY (id)
            );
        """);
        
        resp = self.cassandra.execute("""
            SELECT version FROM version
        """)

        logger.debug("ensure version...")

        self.cassandra.execute("""
            UPDATE version set version = version + 0
            WHERE id = 'version'
        """)

        logger.info("Cassandra schema OK.")

    async def inc_version(self):

        self.cassandra.execute("""
            UPDATE version set version = version + 1
            WHERE id = 'version'
        """)

    async def get_version(self):

        resp = self.cassandra.execute("""
            SELECT version FROM version
            WHERE id = 'version'
        """)

        row = resp.one()

        if row: return row[0]

        return None

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
            SELECT class AS cls, key, value FROM config;
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

                logger.error("Exception occurred", exc_info=True)
                raise e

    async def get_value(self, cls, key):

        while True:

            try:

                resp = self.cassandra.execute(
                    self.get_value_stmt,
                    ( cls, key )
                )

                break

            except Exception as e:

                logger.error("Exception occurred", exc_info=True)
                raise e

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

                logger.error("Exception occurred", exc_info=True)
                raise e

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

                logger.error("Exception occurred", exc_info=True)
                raise e

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

                logger.error("Exception occurred", exc_info=True)
                raise e

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

                logger.error("Exception occurred", exc_info=True)
                raise e

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
                logger.error("Exception occurred", exc_info=True)
                raise e

