"""
IAM Cassandra table store.

Tables:
  - iam_workspaces (id primary key)
  - iam_users (id primary key) + iam_users_by_username lookup table
    (workspace, username) -> id
  - iam_api_keys (key_hash primary key) with secondary index on user_id
  - iam_signing_keys (kid primary key) — RSA keypairs for JWT signing

See docs/tech-specs/iam-protocol.md for the wire-level context.
"""

import logging

from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from ssl import SSLContext, PROTOCOL_TLSv1_2

from . cassandra_async import async_execute

logger = logging.getLogger(__name__)


class IamTableStore:

    def __init__(
            self,
            cassandra_host, cassandra_username, cassandra_password,
            keyspace,
    ):
        self.keyspace = keyspace

        logger.info("IAM: connecting to Cassandra...")

        if isinstance(cassandra_host, str):
            cassandra_host = [h.strip() for h in cassandra_host.split(",")]

        if cassandra_username and cassandra_password:
            ssl_context = SSLContext(PROTOCOL_TLSv1_2)
            auth_provider = PlainTextAuthProvider(
                username=cassandra_username, password=cassandra_password,
            )
            self.cluster = Cluster(
                cassandra_host,
                auth_provider=auth_provider,
                ssl_context=ssl_context,
            )
        else:
            self.cluster = Cluster(cassandra_host)

        self.cassandra = self.cluster.connect()

        logger.info("IAM: connected.")

        self._ensure_schema()
        self._prepare_statements()

    def _ensure_schema(self):
        # FIXME: Replication factor should be configurable.
        self.cassandra.execute(f"""
            create keyspace if not exists {self.keyspace}
                with replication = {{
                    'class' : 'SimpleStrategy',
                    'replication_factor' : 1
                }};
        """)
        self.cassandra.set_keyspace(self.keyspace)

        self.cassandra.execute("""
            CREATE TABLE IF NOT EXISTS iam_workspaces (
                id text PRIMARY KEY,
                name text,
                enabled boolean,
                created timestamp
            );
        """)

        self.cassandra.execute("""
            CREATE TABLE IF NOT EXISTS iam_users (
                id text PRIMARY KEY,
                workspace text,
                username text,
                name text,
                email text,
                password_hash text,
                roles set<text>,
                enabled boolean,
                must_change_password boolean,
                created timestamp
            );
        """)

        self.cassandra.execute("""
            CREATE TABLE IF NOT EXISTS iam_users_by_username (
                workspace text,
                username text,
                user_id text,
                PRIMARY KEY ((workspace), username)
            );
        """)

        self.cassandra.execute("""
            CREATE TABLE IF NOT EXISTS iam_api_keys (
                key_hash text PRIMARY KEY,
                id text,
                user_id text,
                name text,
                prefix text,
                expires timestamp,
                created timestamp,
                last_used timestamp
            );
        """)

        self.cassandra.execute("""
            CREATE INDEX IF NOT EXISTS iam_api_keys_user_id_idx
            ON iam_api_keys (user_id);
        """)

        self.cassandra.execute("""
            CREATE INDEX IF NOT EXISTS iam_api_keys_id_idx
            ON iam_api_keys (id);
        """)

        self.cassandra.execute("""
            CREATE TABLE IF NOT EXISTS iam_signing_keys (
                kid text PRIMARY KEY,
                private_pem text,
                public_pem text,
                created timestamp,
                retired timestamp
            );
        """)

        logger.info("IAM: Cassandra schema OK.")

    def _prepare_statements(self):
        c = self.cassandra

        self.put_workspace_stmt = c.prepare("""
            INSERT INTO iam_workspaces (id, name, enabled, created)
            VALUES (?, ?, ?, ?)
        """)
        self.get_workspace_stmt = c.prepare("""
            SELECT id, name, enabled, created FROM iam_workspaces
            WHERE id = ?
        """)
        self.list_workspaces_stmt = c.prepare("""
            SELECT id, name, enabled, created FROM iam_workspaces
        """)

        self.put_user_stmt = c.prepare("""
            INSERT INTO iam_users (
                id, workspace, username, name, email, password_hash,
                roles, enabled, must_change_password, created
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """)
        self.get_user_stmt = c.prepare("""
            SELECT id, workspace, username, name, email, password_hash,
                   roles, enabled, must_change_password, created
            FROM iam_users WHERE id = ?
        """)
        self.list_users_by_workspace_stmt = c.prepare("""
            SELECT id, workspace, username, name, email, password_hash,
                   roles, enabled, must_change_password, created
            FROM iam_users WHERE workspace = ? ALLOW FILTERING
        """)
        self.list_users_stmt = c.prepare("""
            SELECT id, workspace, username, name, email, password_hash,
                   roles, enabled, must_change_password, created
            FROM iam_users
        """)

        self.put_username_lookup_stmt = c.prepare("""
            INSERT INTO iam_users_by_username (workspace, username, user_id)
            VALUES (?, ?, ?)
        """)
        self.get_user_id_by_username_stmt = c.prepare("""
            SELECT user_id FROM iam_users_by_username
            WHERE workspace = ? AND username = ?
        """)
        self.delete_username_lookup_stmt = c.prepare("""
            DELETE FROM iam_users_by_username
            WHERE workspace = ? AND username = ?
        """)
        self.delete_user_stmt = c.prepare("""
            DELETE FROM iam_users WHERE id = ?
        """)

        self.put_api_key_stmt = c.prepare("""
            INSERT INTO iam_api_keys (
                key_hash, id, user_id, name, prefix, expires,
                created, last_used
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """)
        self.get_api_key_by_hash_stmt = c.prepare("""
            SELECT key_hash, id, user_id, name, prefix, expires,
                   created, last_used
            FROM iam_api_keys WHERE key_hash = ?
        """)
        self.get_api_key_by_id_stmt = c.prepare("""
            SELECT key_hash, id, user_id, name, prefix, expires,
                   created, last_used
            FROM iam_api_keys WHERE id = ?
        """)
        self.list_api_keys_by_user_stmt = c.prepare("""
            SELECT key_hash, id, user_id, name, prefix, expires,
                   created, last_used
            FROM iam_api_keys WHERE user_id = ?
        """)
        self.delete_api_key_stmt = c.prepare("""
            DELETE FROM iam_api_keys WHERE key_hash = ?
        """)

        self.put_signing_key_stmt = c.prepare("""
            INSERT INTO iam_signing_keys (
                kid, private_pem, public_pem, created, retired
            )
            VALUES (?, ?, ?, ?, ?)
        """)
        self.list_signing_keys_stmt = c.prepare("""
            SELECT kid, private_pem, public_pem, created, retired
            FROM iam_signing_keys
        """)
        self.retire_signing_key_stmt = c.prepare("""
            UPDATE iam_signing_keys SET retired = ? WHERE kid = ?
        """)

        self.update_user_profile_stmt = c.prepare("""
            UPDATE iam_users
            SET name = ?, email = ?, roles = ?, enabled = ?,
                must_change_password = ?
            WHERE id = ?
        """)
        self.update_user_password_stmt = c.prepare("""
            UPDATE iam_users
            SET password_hash = ?, must_change_password = ?
            WHERE id = ?
        """)
        self.update_user_enabled_stmt = c.prepare("""
            UPDATE iam_users SET enabled = ? WHERE id = ?
        """)

        self.update_workspace_stmt = c.prepare("""
            UPDATE iam_workspaces SET name = ?, enabled = ?
            WHERE id = ?
        """)

    # ------------------------------------------------------------------
    # Workspaces
    # ------------------------------------------------------------------

    async def put_workspace(self, id, name, enabled, created):
        await async_execute(
            self.cassandra, self.put_workspace_stmt,
            (id, name, enabled, created),
        )

    async def get_workspace(self, id):
        rows = await async_execute(
            self.cassandra, self.get_workspace_stmt, (id,),
        )
        return rows[0] if rows else None

    async def list_workspaces(self):
        return await async_execute(
            self.cassandra, self.list_workspaces_stmt,
        )

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def put_user(
            self, id, workspace, username, name, email, password_hash,
            roles, enabled, must_change_password, created,
    ):
        await async_execute(
            self.cassandra, self.put_user_stmt,
            (
                id, workspace, username, name, email, password_hash,
                set(roles) if roles else set(),
                enabled, must_change_password, created,
            ),
        )
        await async_execute(
            self.cassandra, self.put_username_lookup_stmt,
            (workspace, username, id),
        )

    async def get_user(self, id):
        rows = await async_execute(
            self.cassandra, self.get_user_stmt, (id,),
        )
        return rows[0] if rows else None

    async def get_user_id_by_username(self, workspace, username):
        rows = await async_execute(
            self.cassandra, self.get_user_id_by_username_stmt,
            (workspace, username),
        )
        return rows[0][0] if rows else None

    async def list_users_by_workspace(self, workspace):
        return await async_execute(
            self.cassandra, self.list_users_by_workspace_stmt, (workspace,),
        )

    async def list_users(self):
        """List every user across the deployment.  Used by the
        system-level list-users handler when no workspace filter is
        supplied; the gateway has already authorised the call against
        the caller's authority."""
        return await async_execute(
            self.cassandra, self.list_users_stmt, (),
        )

    async def delete_user(self, id):
        await async_execute(
            self.cassandra, self.delete_user_stmt, (id,),
        )

    async def delete_username_lookup(self, workspace, username):
        await async_execute(
            self.cassandra, self.delete_username_lookup_stmt,
            (workspace, username),
        )

    # ------------------------------------------------------------------
    # API keys
    # ------------------------------------------------------------------

    async def put_api_key(
            self, key_hash, id, user_id, name, prefix, expires,
            created, last_used,
    ):
        await async_execute(
            self.cassandra, self.put_api_key_stmt,
            (key_hash, id, user_id, name, prefix, expires,
             created, last_used),
        )

    async def get_api_key_by_hash(self, key_hash):
        rows = await async_execute(
            self.cassandra, self.get_api_key_by_hash_stmt, (key_hash,),
        )
        return rows[0] if rows else None

    async def get_api_key_by_id(self, id):
        rows = await async_execute(
            self.cassandra, self.get_api_key_by_id_stmt, (id,),
        )
        return rows[0] if rows else None

    async def list_api_keys_by_user(self, user_id):
        return await async_execute(
            self.cassandra, self.list_api_keys_by_user_stmt, (user_id,),
        )

    async def delete_api_key(self, key_hash):
        await async_execute(
            self.cassandra, self.delete_api_key_stmt, (key_hash,),
        )

    # ------------------------------------------------------------------
    # Signing keys
    # ------------------------------------------------------------------

    async def put_signing_key(self, kid, private_pem, public_pem,
                              created, retired):
        await async_execute(
            self.cassandra, self.put_signing_key_stmt,
            (kid, private_pem, public_pem, created, retired),
        )

    async def list_signing_keys(self):
        return await async_execute(
            self.cassandra, self.list_signing_keys_stmt,
        )

    async def retire_signing_key(self, kid, retired):
        await async_execute(
            self.cassandra, self.retire_signing_key_stmt,
            (retired, kid),
        )

    # ------------------------------------------------------------------
    # User partial updates
    # ------------------------------------------------------------------

    async def update_user_profile(
            self, id, name, email, roles, enabled, must_change_password,
    ):
        await async_execute(
            self.cassandra, self.update_user_profile_stmt,
            (
                name, email,
                set(roles) if roles else set(),
                enabled, must_change_password, id,
            ),
        )

    async def update_user_password(
            self, id, password_hash, must_change_password,
    ):
        await async_execute(
            self.cassandra, self.update_user_password_stmt,
            (password_hash, must_change_password, id),
        )

    async def update_user_enabled(self, id, enabled):
        await async_execute(
            self.cassandra, self.update_user_enabled_stmt,
            (enabled, id),
        )

    # ------------------------------------------------------------------
    # Workspace updates
    # ------------------------------------------------------------------

    async def update_workspace(self, id, name, enabled):
        await async_execute(
            self.cassandra, self.update_workspace_stmt,
            (name, enabled, id),
        )

    # ------------------------------------------------------------------
    # Bootstrap helpers
    # ------------------------------------------------------------------

    async def any_workspace_exists(self):
        rows = await self.list_workspaces()
        return bool(rows)
