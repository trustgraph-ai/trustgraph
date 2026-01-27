
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import BatchStatement, SimpleStatement
from ssl import SSLContext, PROTOCOL_TLSv1_2
import os
import logging

# Global list to track clusters for cleanup
_active_clusters = []

logger = logging.getLogger(__name__)

# Sentinel value for wildcard graph queries
GRAPH_WILDCARD = "*"

# Default graph stored as empty string
DEFAULT_GRAPH = ""


class KnowledgeGraph:
    """
    Cassandra-backed knowledge graph supporting quads (s, p, o, g).

    Uses 7 tables to support all 16 query patterns efficiently:
    - Family A (g-wildcard): SPOG, POSG, OSPG
    - Family B (g-specified): GSPO, GPOS, GOSP
    - Collection table: COLL (for iteration/deletion)

    Plus a metadata table for tracking collections.
    """

    def __init__(
            self, hosts=None,
            keyspace="trustgraph", username=None, password=None
    ):

        if hosts is None:
            hosts = ["localhost"]

        self.keyspace = keyspace
        self.username = username

        # 7-table schema for quads with full query pattern support
        # Family A: g-wildcard queries (g in clustering columns)
        self.spog_table = "quads_spog"  # partition (collection, s), cluster (p, o, g)
        self.posg_table = "quads_posg"  # partition (collection, p), cluster (o, s, g)
        self.ospg_table = "quads_ospg"  # partition (collection, o), cluster (s, p, g)

        # Family B: g-specified queries (g in partition key)
        self.gspo_table = "quads_gspo"  # partition (collection, g, s), cluster (p, o)
        self.gpos_table = "quads_gpos"  # partition (collection, g, p), cluster (o, s)
        self.gosp_table = "quads_gosp"  # partition (collection, g, o), cluster (s, p)

        # Collection table for iteration and bulk deletion
        self.coll_table = "quads_coll"  # partition (collection), cluster (g, s, p, o)

        # Collection metadata tracking
        self.collection_metadata_table = "collection_metadata"

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
        """)
        self.init()

    def init(self):
        self.session.execute(f"""
            create keyspace if not exists {self.keyspace}
                with replication = {{
                   'class' : 'SimpleStrategy',
                   'replication_factor' : 1
                }};
        """)

        self.session.set_keyspace(self.keyspace)
        self.init_quad_schema()

    def init_quad_schema(self):
        """Initialize 7-table schema for quads with full query pattern support"""

        # Family A: g-wildcard queries (g in clustering columns)

        # SPOG: partition (collection, s), cluster (p, o, g)
        # Supports: (?, s, ?, ?), (?, s, p, ?), (?, s, p, o)
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.spog_table} (
                collection text,
                s text,
                p text,
                o text,
                g text,
                PRIMARY KEY ((collection, s), p, o, g)
            );
        """)

        # POSG: partition (collection, p), cluster (o, s, g)
        # Supports: (?, ?, p, ?), (?, ?, p, o)
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.posg_table} (
                collection text,
                p text,
                o text,
                s text,
                g text,
                PRIMARY KEY ((collection, p), o, s, g)
            );
        """)

        # OSPG: partition (collection, o), cluster (s, p, g)
        # Supports: (?, ?, ?, o), (?, s, ?, o)
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.ospg_table} (
                collection text,
                o text,
                s text,
                p text,
                g text,
                PRIMARY KEY ((collection, o), s, p, g)
            );
        """)

        # Family B: g-specified queries (g in partition key)

        # GSPO: partition (collection, g, s), cluster (p, o)
        # Supports: (g, s, ?, ?), (g, s, p, ?), (g, s, p, o)
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.gspo_table} (
                collection text,
                g text,
                s text,
                p text,
                o text,
                PRIMARY KEY ((collection, g, s), p, o)
            );
        """)

        # GPOS: partition (collection, g, p), cluster (o, s)
        # Supports: (g, ?, p, ?), (g, ?, p, o)
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.gpos_table} (
                collection text,
                g text,
                p text,
                o text,
                s text,
                PRIMARY KEY ((collection, g, p), o, s)
            );
        """)

        # GOSP: partition (collection, g, o), cluster (s, p)
        # Supports: (g, ?, ?, o), (g, s, ?, o)
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.gosp_table} (
                collection text,
                g text,
                o text,
                s text,
                p text,
                PRIMARY KEY ((collection, g, o), s, p)
            );
        """)

        # Collection table for iteration and bulk deletion
        # COLL: partition (collection), cluster (g, s, p, o)
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.coll_table} (
                collection text,
                g text,
                s text,
                p text,
                o text,
                PRIMARY KEY (collection, g, s, p, o)
            );
        """)

        # Collection metadata tracking
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.collection_metadata_table} (
                collection text,
                created_at timestamp,
                PRIMARY KEY (collection)
            );
        """)

        logger.info("Quad schema initialized (7 tables + metadata)")

    def prepare_statements(self):
        """Prepare statements for all 7 tables"""

        # Insert statements
        self.insert_spog_stmt = self.session.prepare(
            f"INSERT INTO {self.spog_table} (collection, s, p, o, g) VALUES (?, ?, ?, ?, ?)"
        )
        self.insert_posg_stmt = self.session.prepare(
            f"INSERT INTO {self.posg_table} (collection, p, o, s, g) VALUES (?, ?, ?, ?, ?)"
        )
        self.insert_ospg_stmt = self.session.prepare(
            f"INSERT INTO {self.ospg_table} (collection, o, s, p, g) VALUES (?, ?, ?, ?, ?)"
        )
        self.insert_gspo_stmt = self.session.prepare(
            f"INSERT INTO {self.gspo_table} (collection, g, s, p, o) VALUES (?, ?, ?, ?, ?)"
        )
        self.insert_gpos_stmt = self.session.prepare(
            f"INSERT INTO {self.gpos_table} (collection, g, p, o, s) VALUES (?, ?, ?, ?, ?)"
        )
        self.insert_gosp_stmt = self.session.prepare(
            f"INSERT INTO {self.gosp_table} (collection, g, o, s, p) VALUES (?, ?, ?, ?, ?)"
        )
        self.insert_coll_stmt = self.session.prepare(
            f"INSERT INTO {self.coll_table} (collection, g, s, p, o) VALUES (?, ?, ?, ?, ?)"
        )

        # Delete statements (for single quad deletion)
        self.delete_spog_stmt = self.session.prepare(
            f"DELETE FROM {self.spog_table} WHERE collection = ? AND s = ? AND p = ? AND o = ? AND g = ?"
        )
        self.delete_posg_stmt = self.session.prepare(
            f"DELETE FROM {self.posg_table} WHERE collection = ? AND p = ? AND o = ? AND s = ? AND g = ?"
        )
        self.delete_ospg_stmt = self.session.prepare(
            f"DELETE FROM {self.ospg_table} WHERE collection = ? AND o = ? AND s = ? AND p = ? AND g = ?"
        )
        self.delete_gspo_stmt = self.session.prepare(
            f"DELETE FROM {self.gspo_table} WHERE collection = ? AND g = ? AND s = ? AND p = ? AND o = ?"
        )
        self.delete_gpos_stmt = self.session.prepare(
            f"DELETE FROM {self.gpos_table} WHERE collection = ? AND g = ? AND p = ? AND o = ? AND s = ?"
        )
        self.delete_gosp_stmt = self.session.prepare(
            f"DELETE FROM {self.gosp_table} WHERE collection = ? AND g = ? AND o = ? AND s = ? AND p = ?"
        )
        self.delete_coll_stmt = self.session.prepare(
            f"DELETE FROM {self.coll_table} WHERE collection = ? AND g = ? AND s = ? AND p = ? AND o = ?"
        )

        # Query statements - Family A (g-wildcard, g in clustering)

        # SPOG table queries
        self.get_s_wildcard_stmt = self.session.prepare(
            f"SELECT p, o, g FROM {self.spog_table} WHERE collection = ? AND s = ? LIMIT ?"
        )
        self.get_sp_wildcard_stmt = self.session.prepare(
            f"SELECT o, g FROM {self.spog_table} WHERE collection = ? AND s = ? AND p = ? LIMIT ?"
        )
        self.get_spo_wildcard_stmt = self.session.prepare(
            f"SELECT g FROM {self.spog_table} WHERE collection = ? AND s = ? AND p = ? AND o = ? LIMIT ?"
        )

        # POSG table queries
        self.get_p_wildcard_stmt = self.session.prepare(
            f"SELECT o, s, g FROM {self.posg_table} WHERE collection = ? AND p = ? LIMIT ?"
        )
        self.get_po_wildcard_stmt = self.session.prepare(
            f"SELECT s, g FROM {self.posg_table} WHERE collection = ? AND p = ? AND o = ? LIMIT ?"
        )

        # OSPG table queries
        self.get_o_wildcard_stmt = self.session.prepare(
            f"SELECT s, p, g FROM {self.ospg_table} WHERE collection = ? AND o = ? LIMIT ?"
        )
        self.get_os_wildcard_stmt = self.session.prepare(
            f"SELECT p, g FROM {self.ospg_table} WHERE collection = ? AND o = ? AND s = ? LIMIT ?"
        )

        # Query statements - Family B (g-specified, g in partition)

        # GSPO table queries
        self.get_gs_stmt = self.session.prepare(
            f"SELECT p, o FROM {self.gspo_table} WHERE collection = ? AND g = ? AND s = ? LIMIT ?"
        )
        self.get_gsp_stmt = self.session.prepare(
            f"SELECT o FROM {self.gspo_table} WHERE collection = ? AND g = ? AND s = ? AND p = ? LIMIT ?"
        )
        self.get_gspo_stmt = self.session.prepare(
            f"SELECT s FROM {self.gspo_table} WHERE collection = ? AND g = ? AND s = ? AND p = ? AND o = ? LIMIT ?"
        )

        # GPOS table queries
        self.get_gp_stmt = self.session.prepare(
            f"SELECT o, s FROM {self.gpos_table} WHERE collection = ? AND g = ? AND p = ? LIMIT ?"
        )
        self.get_gpo_stmt = self.session.prepare(
            f"SELECT s FROM {self.gpos_table} WHERE collection = ? AND g = ? AND p = ? AND o = ? LIMIT ?"
        )

        # GOSP table queries
        self.get_go_stmt = self.session.prepare(
            f"SELECT s, p FROM {self.gosp_table} WHERE collection = ? AND g = ? AND o = ? LIMIT ?"
        )
        self.get_gos_stmt = self.session.prepare(
            f"SELECT p FROM {self.gosp_table} WHERE collection = ? AND g = ? AND o = ? AND s = ? LIMIT ?"
        )

        # Collection table query (for get_all and iteration)
        self.get_all_stmt = self.session.prepare(
            f"SELECT g, s, p, o FROM {self.coll_table} WHERE collection = ? LIMIT ?"
        )
        self.get_g_stmt = self.session.prepare(
            f"SELECT s, p, o FROM {self.coll_table} WHERE collection = ? AND g = ? LIMIT ?"
        )

        logger.info("Prepared statements initialized for quad schema (7 tables)")

    def insert(self, collection, s, p, o, g=None):
        """Insert a quad into all 7 tables"""
        # Default graph stored as empty string
        if g is None:
            g = DEFAULT_GRAPH

        batch = BatchStatement()

        # Family A tables
        batch.add(self.insert_spog_stmt, (collection, s, p, o, g))
        batch.add(self.insert_posg_stmt, (collection, p, o, s, g))
        batch.add(self.insert_ospg_stmt, (collection, o, s, p, g))

        # Family B tables
        batch.add(self.insert_gspo_stmt, (collection, g, s, p, o))
        batch.add(self.insert_gpos_stmt, (collection, g, p, o, s))
        batch.add(self.insert_gosp_stmt, (collection, g, o, s, p))

        # Collection table
        batch.add(self.insert_coll_stmt, (collection, g, s, p, o))

        self.session.execute(batch)

    def delete_quad(self, collection, s, p, o, g=None):
        """Delete a single quad from all 7 tables"""
        if g is None:
            g = DEFAULT_GRAPH

        batch = BatchStatement()

        batch.add(self.delete_spog_stmt, (collection, s, p, o, g))
        batch.add(self.delete_posg_stmt, (collection, p, o, s, g))
        batch.add(self.delete_ospg_stmt, (collection, o, s, p, g))
        batch.add(self.delete_gspo_stmt, (collection, g, s, p, o))
        batch.add(self.delete_gpos_stmt, (collection, g, p, o, s))
        batch.add(self.delete_gosp_stmt, (collection, g, o, s, p))
        batch.add(self.delete_coll_stmt, (collection, g, s, p, o))

        self.session.execute(batch)

    # ========================================================================
    # Query methods
    # g=None means default graph, g="*" means all graphs
    # ========================================================================

    def get_all(self, collection, limit=50):
        """Get all quads in collection"""
        return self.session.execute(self.get_all_stmt, (collection, limit))

    def get_s(self, collection, s, g=None, limit=10):
        """Query by subject. g=None: default graph, g='*': all graphs"""
        if g is None or g == DEFAULT_GRAPH:
            # Default graph - use GSPO table
            return self.session.execute(self.get_gs_stmt, (collection, DEFAULT_GRAPH, s, limit))
        elif g == GRAPH_WILDCARD:
            # All graphs - use SPOG table
            return self.session.execute(self.get_s_wildcard_stmt, (collection, s, limit))
        else:
            # Specific graph - use GSPO table
            return self.session.execute(self.get_gs_stmt, (collection, g, s, limit))

    def get_p(self, collection, p, g=None, limit=10):
        """Query by predicate"""
        if g is None or g == DEFAULT_GRAPH:
            return self.session.execute(self.get_gp_stmt, (collection, DEFAULT_GRAPH, p, limit))
        elif g == GRAPH_WILDCARD:
            return self.session.execute(self.get_p_wildcard_stmt, (collection, p, limit))
        else:
            return self.session.execute(self.get_gp_stmt, (collection, g, p, limit))

    def get_o(self, collection, o, g=None, limit=10):
        """Query by object"""
        if g is None or g == DEFAULT_GRAPH:
            return self.session.execute(self.get_go_stmt, (collection, DEFAULT_GRAPH, o, limit))
        elif g == GRAPH_WILDCARD:
            return self.session.execute(self.get_o_wildcard_stmt, (collection, o, limit))
        else:
            return self.session.execute(self.get_go_stmt, (collection, g, o, limit))

    def get_sp(self, collection, s, p, g=None, limit=10):
        """Query by subject and predicate"""
        if g is None or g == DEFAULT_GRAPH:
            return self.session.execute(self.get_gsp_stmt, (collection, DEFAULT_GRAPH, s, p, limit))
        elif g == GRAPH_WILDCARD:
            return self.session.execute(self.get_sp_wildcard_stmt, (collection, s, p, limit))
        else:
            return self.session.execute(self.get_gsp_stmt, (collection, g, s, p, limit))

    def get_po(self, collection, p, o, g=None, limit=10):
        """Query by predicate and object"""
        if g is None or g == DEFAULT_GRAPH:
            return self.session.execute(self.get_gpo_stmt, (collection, DEFAULT_GRAPH, p, o, limit))
        elif g == GRAPH_WILDCARD:
            return self.session.execute(self.get_po_wildcard_stmt, (collection, p, o, limit))
        else:
            return self.session.execute(self.get_gpo_stmt, (collection, g, p, o, limit))

    def get_os(self, collection, o, s, g=None, limit=10):
        """Query by object and subject"""
        if g is None or g == DEFAULT_GRAPH:
            return self.session.execute(self.get_gos_stmt, (collection, DEFAULT_GRAPH, o, s, limit))
        elif g == GRAPH_WILDCARD:
            return self.session.execute(self.get_os_wildcard_stmt, (collection, o, s, limit))
        else:
            return self.session.execute(self.get_gos_stmt, (collection, g, o, s, limit))

    def get_spo(self, collection, s, p, o, g=None, limit=10):
        """Query by subject, predicate, object (find which graphs)"""
        if g is None or g == DEFAULT_GRAPH:
            return self.session.execute(self.get_gspo_stmt, (collection, DEFAULT_GRAPH, s, p, o, limit))
        elif g == GRAPH_WILDCARD:
            return self.session.execute(self.get_spo_wildcard_stmt, (collection, s, p, o, limit))
        else:
            return self.session.execute(self.get_gspo_stmt, (collection, g, s, p, o, limit))

    def get_g(self, collection, g, limit=50):
        """Get all quads in a specific graph"""
        if g is None:
            g = DEFAULT_GRAPH
        return self.session.execute(self.get_g_stmt, (collection, g, limit))

    # ========================================================================
    # Collection management
    # ========================================================================

    def collection_exists(self, collection):
        """Check if collection exists"""
        try:
            result = self.session.execute(
                f"SELECT collection FROM {self.collection_metadata_table} WHERE collection = %s LIMIT 1",
                (collection,)
            )
            return bool(list(result))
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False

    def create_collection(self, collection):
        """Create collection by inserting metadata row"""
        try:
            import datetime
            self.session.execute(
                f"INSERT INTO {self.collection_metadata_table} (collection, created_at) VALUES (%s, %s)",
                (collection, datetime.datetime.now())
            )
            logger.info(f"Created collection metadata for {collection}")
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise e

    def delete_collection(self, collection):
        """Delete all quads for a collection from all 7 tables"""
        # Read all quads from collection table
        rows = self.session.execute(
            f"SELECT g, s, p, o FROM {self.coll_table} WHERE collection = %s",
            (collection,)
        )

        batch = BatchStatement()
        count = 0

        for row in rows:
            g, s, p, o = row.g, row.s, row.p, row.o

            # Delete from all 7 tables
            batch.add(self.delete_spog_stmt, (collection, s, p, o, g))
            batch.add(self.delete_posg_stmt, (collection, p, o, s, g))
            batch.add(self.delete_ospg_stmt, (collection, o, s, p, g))
            batch.add(self.delete_gspo_stmt, (collection, g, s, p, o))
            batch.add(self.delete_gpos_stmt, (collection, g, p, o, s))
            batch.add(self.delete_gosp_stmt, (collection, g, o, s, p))
            batch.add(self.delete_coll_stmt, (collection, g, s, p, o))

            count += 1

            # Execute batch every 15 quads (7 deletes each = 105 statements)
            if count % 15 == 0:
                self.session.execute(batch)
                batch = BatchStatement()

        # Execute remaining
        if count % 15 != 0:
            self.session.execute(batch)

        # Delete collection metadata
        self.session.execute(
            f"DELETE FROM {self.collection_metadata_table} WHERE collection = %s",
            (collection,)
        )

        logger.info(f"Deleted {count} quads from collection {collection}")

    def close(self):
        """Close connections"""
        if hasattr(self, 'session') and self.session:
            self.session.shutdown()
        if hasattr(self, 'cluster') and self.cluster:
            self.cluster.shutdown()
            if self.cluster in _active_clusters:
                _active_clusters.remove(self.cluster)
