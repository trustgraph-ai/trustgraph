
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import BatchStatement, SimpleStatement
from ssl import SSLContext, PROTOCOL_TLSv1_2
import os
import logging

# Global list to track clusters for cleanup
_active_clusters = []

logger = logging.getLogger(__name__)

class KnowledgeGraph:

    def __init__(
            self, hosts=None,
            keyspace="trustgraph", username=None, password=None
    ):

        if hosts is None:
            hosts = ["localhost"]

        self.keyspace = keyspace
        self.username = username

        # Optimized multi-table schema
        self.subject_table = "triples_s"
        self.po_table = "triples_p"
        self.object_table = "triples_o"

        if username and password:
            ssl_context = SSLContext(PROTOCOL_TLSv1_2)
            auth_provider = PlainTextAuthProvider(username=username, password=password)
            self.cluster = Cluster(hosts, auth_provider=auth_provider, ssl_context=ssl_context)
        else:
            self.cluster = Cluster(hosts)
        self.session = self.cluster.connect()

        # Track this cluster globally
        _active_clusters.append(self.cluster)

        self.init()
        self.prepare_statements()

    def clear(self):

        self.session.execute(f"""
            drop keyspace if exists {self.keyspace};
        """);

        self.init()

    def init(self):

        self.session.execute(f"""
            create keyspace if not exists {self.keyspace}
                with replication = {{
                   'class' : 'SimpleStrategy',
                   'replication_factor' : 1
                }};
        """);

        self.session.set_keyspace(self.keyspace)
        self.init_optimized_schema()


    def init_optimized_schema(self):
        """Initialize optimized multi-table schema for performance"""
        # Table 1: Subject-centric queries (get_s, get_sp, get_spo, get_os)
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.subject_table} (
                collection text,
                s text,
                p text,
                o text,
                PRIMARY KEY (collection, s, p, o)
            );
        """);

        # Table 2: Predicate-Object queries (get_p, get_po) - eliminates ALLOW FILTERING!
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.po_table} (
                collection text,
                p text,
                o text,
                s text,
                PRIMARY KEY (collection, p, o, s)
            );
        """);

        # Table 3: Object-centric queries (get_o)
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.object_table} (
                collection text,
                o text,
                s text,
                p text,
                PRIMARY KEY (collection, o, s, p)
            );
        """);

        logger.info("Optimized multi-table schema initialized")

    def prepare_statements(self):
        """Prepare statements for optimal performance"""
        # Insert statements for batch operations
        self.insert_subject_stmt = self.session.prepare(
            f"INSERT INTO {self.subject_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
        )

        self.insert_po_stmt = self.session.prepare(
            f"INSERT INTO {self.po_table} (collection, p, o, s) VALUES (?, ?, ?, ?)"
        )

        self.insert_object_stmt = self.session.prepare(
            f"INSERT INTO {self.object_table} (collection, o, s, p) VALUES (?, ?, ?, ?)"
        )

        # Query statements for optimized access
        self.get_all_stmt = self.session.prepare(
            f"SELECT s, p, o FROM {self.subject_table} WHERE collection = ? LIMIT ? ALLOW FILTERING"
        )

        self.get_s_stmt = self.session.prepare(
            f"SELECT p, o FROM {self.subject_table} WHERE collection = ? AND s = ? LIMIT ?"
        )

        self.get_p_stmt = self.session.prepare(
            f"SELECT s, o FROM {self.po_table} WHERE collection = ? AND p = ? LIMIT ?"
        )

        self.get_o_stmt = self.session.prepare(
            f"SELECT s, p FROM {self.object_table} WHERE collection = ? AND o = ? LIMIT ?"
        )

        self.get_sp_stmt = self.session.prepare(
            f"SELECT o FROM {self.subject_table} WHERE collection = ? AND s = ? AND p = ? LIMIT ?"
        )

        # The critical optimization: get_po without ALLOW FILTERING!
        self.get_po_stmt = self.session.prepare(
            f"SELECT s FROM {self.po_table} WHERE collection = ? AND p = ? AND o = ? LIMIT ?"
        )

        self.get_os_stmt = self.session.prepare(
            f"SELECT p FROM {self.object_table} WHERE collection = ? AND o = ? AND s = ? LIMIT ?"
        )

        self.get_spo_stmt = self.session.prepare(
            f"SELECT s as x FROM {self.subject_table} WHERE collection = ? AND s = ? AND p = ? AND o = ? LIMIT ?"
        )

        logger.info("Prepared statements initialized for optimal performance")

    def insert(self, collection, s, p, o):
        # Batch write to all three tables for consistency
        batch = BatchStatement()

        # Insert into subject table
        batch.add(self.insert_subject_stmt, (collection, s, p, o))

        # Insert into predicate-object table (column order: collection, p, o, s)
        batch.add(self.insert_po_stmt, (collection, p, o, s))

        # Insert into object table (column order: collection, o, s, p)
        batch.add(self.insert_object_stmt, (collection, o, s, p))

        self.session.execute(batch)

    def get_all(self, collection, limit=50):
        # Use subject table for get_all queries
        return self.session.execute(
            self.get_all_stmt,
            (collection, limit)
        )

    def get_s(self, collection, s, limit=10):
        # Optimized: Direct partition access with (collection, s)
        return self.session.execute(
            self.get_s_stmt,
            (collection, s, limit)
        )

    def get_p(self, collection, p, limit=10):
        # Optimized: Use po_table for direct partition access
        return self.session.execute(
            self.get_p_stmt,
            (collection, p, limit)
        )

    def get_o(self, collection, o, limit=10):
        # Optimized: Use object_table for direct partition access
        return self.session.execute(
            self.get_o_stmt,
            (collection, o, limit)
        )

    def get_sp(self, collection, s, p, limit=10):
        # Optimized: Use subject_table with clustering key access
        return self.session.execute(
            self.get_sp_stmt,
            (collection, s, p, limit)
        )

    def get_po(self, collection, p, o, limit=10):
        # CRITICAL OPTIMIZATION: Use po_table - NO MORE ALLOW FILTERING!
        return self.session.execute(
            self.get_po_stmt,
            (collection, p, o, limit)
        )

    def get_os(self, collection, o, s, limit=10):
        # Optimized: Use subject_table with clustering access (no more ALLOW FILTERING)
        return self.session.execute(
            self.get_os_stmt,
            (collection, s, o, limit)
        )

    def get_spo(self, collection, s, p, o, limit=10):
        # Optimized: Use subject_table for exact key lookup
        return self.session.execute(
            self.get_spo_stmt,
            (collection, s, p, o, limit)
        )

    def delete_collection(self, collection):
        """Delete all triples for a specific collection"""
        # Delete from all three tables
        self.session.execute(
            f"delete from {self.subject_table} where collection = %s",
            (collection,)
        )
        self.session.execute(
            f"delete from {self.po_table} where collection = %s",
            (collection,)
        )
        self.session.execute(
            f"delete from {self.object_table} where collection = %s",
            (collection,)
        )

    def close(self):
        """Close the Cassandra session and cluster connections properly"""
        if hasattr(self, 'session') and self.session:
            self.session.shutdown()
        if hasattr(self, 'cluster') and self.cluster:
            self.cluster.shutdown()
            # Remove from global tracking
            if self.cluster in _active_clusters:
                _active_clusters.remove(self.cluster)
