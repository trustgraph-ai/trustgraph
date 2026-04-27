
from .. schema import KnowledgeResponse, Triple, Triples, EntityEmbeddings
from .. schema import Metadata, GraphEmbeddings

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from ssl import SSLContext, PROTOCOL_TLSv1_2

import uuid
import time
import asyncio
import logging

from . cassandra_async import async_execute

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
                workspace text,
                class text,
                key text,
                value text,
                PRIMARY KEY ((workspace, class), key)
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

        await async_execute(self.cassandra, """
            UPDATE version set version = version + 1
            WHERE id = 'version'
        """)

    async def get_version(self):

        rows = await async_execute(self.cassandra, """
            SELECT version FROM version
            WHERE id = 'version'
        """)

        if rows:
            return rows[0][0]

        return None

    def prepare_statements(self):

        self.put_config_stmt = self.cassandra.prepare("""
            INSERT INTO config ( workspace, class, key, value )
            VALUES (?, ?, ?, ?)
        """)

        self.get_keys_stmt = self.cassandra.prepare("""
            SELECT key FROM config
            WHERE workspace = ? AND class = ?;
        """)

        self.get_value_stmt = self.cassandra.prepare("""
            SELECT value FROM config
            WHERE workspace = ? AND class = ? AND key = ?;
        """)

        self.delete_key_stmt = self.cassandra.prepare("""
            DELETE FROM config
            WHERE workspace = ? AND class = ? AND key = ?;
        """)

        self.get_all_stmt = self.cassandra.prepare("""
            SELECT workspace, class AS cls, key, value FROM config;
        """)

        self.get_all_for_workspace_stmt = self.cassandra.prepare("""
            SELECT class AS cls, key, value FROM config
            WHERE workspace = ?
            ALLOW FILTERING;
        """)

        self.get_values_stmt = self.cassandra.prepare("""
            SELECT key, value FROM config
            WHERE workspace = ? AND class = ?;
        """)

        self.get_values_all_ws_stmt = self.cassandra.prepare("""
            SELECT workspace, key, value FROM config
            WHERE class = ?
            ALLOW FILTERING;
        """)

    async def put_config(self, workspace, cls, key, value):
        try:
            await async_execute(
                self.cassandra,
                self.put_config_stmt,
                (workspace, cls, key, value),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

    async def get_value(self, workspace, cls, key):
        try:
            rows = await async_execute(
                self.cassandra,
                self.get_value_stmt,
                (workspace, cls, key),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        for row in rows:
            return row[0]
        return None

    async def get_values(self, workspace, cls):
        try:
            rows = await async_execute(
                self.cassandra,
                self.get_values_stmt,
                (workspace, cls),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        return [[row[0], row[1]] for row in rows]

    async def get_values_all_ws(self, cls):
        """Return (workspace, key, value) tuples for all workspaces
        with entries of the given class."""
        try:
            rows = await async_execute(
                self.cassandra,
                self.get_values_all_ws_stmt,
                (cls,),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        return [(row[0], row[1], row[2]) for row in rows]

    async def get_all(self):
        try:
            rows = await async_execute(
                self.cassandra,
                self.get_all_stmt,
                (),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        return [(row[0], row[1], row[2], row[3]) for row in rows]

    async def get_all_for_workspace(self, workspace):
        try:
            rows = await async_execute(
                self.cassandra,
                self.get_all_for_workspace_stmt,
                (workspace,),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        return [(row[0], row[1], row[2]) for row in rows]

    async def get_keys(self, workspace, cls):
        try:
            rows = await async_execute(
                self.cassandra,
                self.get_keys_stmt,
                (workspace, cls),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

        return [row[0] for row in rows]

    async def delete_key(self, workspace, cls, key):
        try:
            await async_execute(
                self.cassandra,
                self.delete_key_stmt,
                (workspace, cls, key),
            )
        except Exception:
            logger.error("Exception occurred", exc_info=True)
            raise

