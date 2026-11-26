
import asyncio
import datetime
import os
import logging
import re
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider
from cassandra.query import BatchStatement, SimpleStatement
import ssl

from ..tables.cassandra_async import async_execute, async_scan

# Global list to track clusters for cleanup
_active_clusters = []

logger = logging.getLogger(__name__)

# Sentinel value for wildcard graph queries
GRAPH_WILDCARD = "*"

# Default graph stored as empty string
DEFAULT_GRAPH = ""


class KnowledgeGraph:
    """
    REDUNDANT: This 7-table implementation has been superseded by
    EntityCentricKnowledgeGraph which uses a more efficient 2-table model.
    This class is retained temporarily for reference but should not be used
    for new deployments.

    Cassandra-backed knowledge graph supporting quads (s, p, o, g).

    Uses 7 tables to support all 16 query patterns efficiently:
    - Family A (g-wildcard): SPOG, POSG, OSPG
    - Family B (g-specified): GSPO, GPOS, GOSP
    - Collection table: COLL (for iteration/deletion)

    Plus a metadata table for tracking collections.
    """

    def __init__(
            self, hosts=None,
            keyspace="trustgraph", username=None, password=None,
            replication_factor=1,
    ):

        if hosts is None:
            hosts = ["localhost"]

        self.keyspace = keyspace
        self.replication_factor = replication_factor
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
            ssl_context = ssl.create_default_context()
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
                   'replication_factor' : {self.replication_factor}
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


class EntityCentricKnowledgeGraph:
    """
    Entity-centric Cassandra-backed knowledge graph with append-only versioning.

    Tables:
    - quads_by_entity: versioned quad storage (version DESC per quad)
    - quads_by_collection: manifest for collection-level queries
    - graph_versions: current version per (collection, named_graph)
    - graph_version_log: version history with timestamps and labels
    """

    def __init__(
            self, hosts=None,
            keyspace="trustgraph", username=None, password=None,
            replication_factor=1,
    ):

        if hosts is None:
            hosts = ["localhost"]

        self.keyspace = self.sanitize_name(keyspace)
        self.replication_factor = replication_factor
        self.username = username

        self.entity_table = "quads_by_entity"
        self.collection_table = "quads_by_collection"
        self.collection_metadata_table = "collection_metadata"
        self.graph_versions_table = "graph_versions"
        self.graph_version_log_table = "graph_version_log"

        if username and password:
            ssl_context = ssl.create_default_context()
            auth_provider = PlainTextAuthProvider(username=username, password=password)
            self.cluster = Cluster(hosts, auth_provider=auth_provider, ssl_context=ssl_context)
        else:
            self.cluster = Cluster(hosts)
        self.session = self.cluster.connect()

        # Track this cluster globally
        _active_clusters.append(self.cluster)

        self.init()
        self.prepare_statements()
        
    def sanitize_name(self, name: str) -> str:
        """Sanitize names for Cassandra compatibility"""
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if safe_name and not safe_name[0].isalpha():
            safe_name = 'r_' + safe_name
        return safe_name.lower()

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
                   'replication_factor' : {self.replication_factor}
                }};
        """)

        self.session.set_keyspace(self.keyspace)
        self.init_entity_centric_schema()

    def init_entity_centric_schema(self):
        """Initialize entity-centric schema with version support"""

        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.entity_table} (
                collection text,
                entity     text,
                role       text,
                p          text,
                otype      text,
                s          text,
                o          text,
                g          text,
                dtype      text,
                lang       text,
                version    bigint,
                is_deleted boolean,
                PRIMARY KEY ((collection, entity), role, p, otype, s, o, g, dtype, lang, version)
            ) WITH CLUSTERING ORDER BY (
                role ASC, p ASC, otype ASC, s ASC, o ASC,
                g ASC, dtype ASC, lang ASC, version DESC
            );
        """)

        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.collection_table} (
                collection text,
                g          text,
                s          text,
                p          text,
                o          text,
                otype      text,
                dtype      text,
                lang       text,
                version    bigint,
                is_deleted boolean,
                PRIMARY KEY (
                    (collection),
                    g, s, p, o, otype, dtype, lang, version
                )
            ) WITH CLUSTERING ORDER BY (
                g ASC, s ASC, p ASC, o ASC,
                otype ASC, dtype ASC, lang ASC, version DESC
            );
        """)

        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.collection_metadata_table} (
                collection text,
                created_at timestamp,
                PRIMARY KEY (collection)
            );
        """)

        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.graph_versions_table} (
                collection      text,
                named_graph     text,
                current_version bigint,
                PRIMARY KEY ((collection), named_graph)
            );
        """)

        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.graph_version_log_table} (
                collection      text,
                named_graph     text,
                version         bigint,
                created_at      timestamp,
                names           set<text>,
                description     text,
                PRIMARY KEY ((collection, named_graph), version)
            ) WITH CLUSTERING ORDER BY (version DESC);
        """)

        logger.info("Entity-centric schema initialized with version support")

    def prepare_statements(self):

        self.insert_entity_stmt = self.session.prepare(
            f"INSERT INTO {self.entity_table} "
            "(collection, entity, role, p, otype, s, o, g, dtype, lang, version, is_deleted) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )

        self.insert_collection_stmt = self.session.prepare(
            f"INSERT INTO {self.collection_table} "
            "(collection, g, s, p, o, otype, dtype, lang, version, is_deleted) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        )

        self.get_entity_as_s_stmt = self.session.prepare(
            f"SELECT p, otype, s, o, g, dtype, lang, version, is_deleted "
            f"FROM {self.entity_table} "
            "WHERE collection = ? AND entity = ? AND role = 'S'"
        )

        self.get_entity_as_s_p_stmt = self.session.prepare(
            f"SELECT otype, s, o, g, dtype, lang, version, is_deleted "
            f"FROM {self.entity_table} "
            "WHERE collection = ? AND entity = ? AND role = 'S' AND p = ?"
        )

        self.get_entity_as_s_p_otype_stmt = self.session.prepare(
            f"SELECT s, o, g, dtype, lang, version, is_deleted "
            f"FROM {self.entity_table} "
            "WHERE collection = ? AND entity = ? AND role = 'S' AND p = ? AND otype = ?"
        )

        self.get_entity_as_p_stmt = self.session.prepare(
            f"SELECT p, otype, s, o, g, dtype, lang, version, is_deleted "
            f"FROM {self.entity_table} "
            "WHERE collection = ? AND entity = ? AND role = 'P'"
        )

        self.get_entity_as_o_stmt = self.session.prepare(
            f"SELECT p, otype, s, o, g, dtype, lang, version, is_deleted "
            f"FROM {self.entity_table} "
            "WHERE collection = ? AND entity = ? AND role = 'O'"
        )

        self.get_entity_as_o_p_stmt = self.session.prepare(
            f"SELECT otype, s, o, g, dtype, lang, version, is_deleted "
            f"FROM {self.entity_table} "
            "WHERE collection = ? AND entity = ? AND role = 'O' AND p = ?"
        )

        self.get_entity_as_g_stmt = self.session.prepare(
            f"SELECT p, otype, s, o, g, dtype, lang, version, is_deleted "
            f"FROM {self.entity_table} "
            "WHERE collection = ? AND entity = ? AND role = 'G'"
        )

        # Note: no prepared statements for whole-collection / per-graph scans.
        # Those paths resolve version history in-process and need to over-fetch
        # beyond the user's result limit, so they build SimpleStatements with
        # fetch_size and iterate pages (see async_get_all / _resolve_collection).

        self.delete_entity_partition_stmt = self.session.prepare(
            f"DELETE FROM {self.entity_table} WHERE collection = ? AND entity = ?"
        )

        self.delete_collection_row_stmt = self.session.prepare(
            f"DELETE FROM {self.collection_table} "
            "WHERE collection = ? AND g = ? AND s = ? AND p = ? AND o = ? "
            "AND otype = ? AND dtype = ? AND lang = ?"
        )

        self.get_graph_version_stmt = self.session.prepare(
            f"SELECT current_version FROM {self.graph_versions_table} "
            "WHERE collection = ? AND named_graph = ?"
        )

        self.get_version_map_stmt = self.session.prepare(
            f"SELECT named_graph, current_version FROM {self.graph_versions_table} "
            "WHERE collection = ?"
        )

        self.set_graph_version_stmt = self.session.prepare(
            f"INSERT INTO {self.graph_versions_table} "
            "(collection, named_graph, current_version) VALUES (?, ?, ?)"
        )

        self.insert_version_log_stmt = self.session.prepare(
            f"INSERT INTO {self.graph_version_log_table} "
            "(collection, named_graph, version, created_at, description) "
            "VALUES (?, ?, ?, ?, ?)"
        )

        self.get_version_log_stmt = self.session.prepare(
            f"SELECT version, created_at, names, description "
            f"FROM {self.graph_version_log_table} "
            "WHERE collection = ? AND named_graph = ?"
        )

        self.add_version_label_stmt = self.session.prepare(
            f"UPDATE {self.graph_version_log_table} "
            "SET names = names + ? "
            "WHERE collection = ? AND named_graph = ? AND version = ?"
        )

        self.set_version_description_stmt = self.session.prepare(
            f"UPDATE {self.graph_version_log_table} "
            "SET description = ? "
            "WHERE collection = ? AND named_graph = ? AND version = ?"
        )

        self.get_entity_as_s_all_stmt = self.session.prepare(
            f"SELECT p, otype, s, o, g, dtype, lang, version, is_deleted "
            f"FROM {self.entity_table} "
            "WHERE collection = ? AND entity = ? AND role = 'S'"
        )

        self.delete_collection_version_stmt = self.session.prepare(
            f"DELETE FROM {self.collection_table} "
            "WHERE collection = ? AND g = ? AND s = ? AND p = ? AND o = ? "
            "AND otype = ? AND dtype = ? AND lang = ? AND version = ?"
        )

        self.delete_entity_version_stmt = self.session.prepare(
            f"DELETE FROM {self.entity_table} "
            "WHERE collection = ? AND entity = ? AND role = ? "
            "AND p = ? AND otype = ? AND s = ? AND o = ? AND g = ? "
            "AND dtype = ? AND lang = ? AND version = ?"
        )

        self.delete_version_log_stmt = self.session.prepare(
            f"DELETE FROM {self.graph_version_log_table} "
            "WHERE collection = ? AND named_graph = ? AND version = ?"
        )

        logger.info("Prepared statements initialized")

    def insert(self, collection, s, p, o, g, version, is_deleted,
               otype, dtype="", lang=""):
        if g is None:
            g = DEFAULT_GRAPH

        batch = BatchStatement()

        batch.add(self.insert_entity_stmt, (
            collection, s, 'S', p, otype, s, o, g, dtype, lang,
            version, is_deleted,
        ))
        batch.add(self.insert_entity_stmt, (
            collection, p, 'P', p, otype, s, o, g, dtype, lang,
            version, is_deleted,
        ))
        batch.add(self.insert_entity_stmt, (
            collection, o, 'O', p, otype, s, o, g, dtype, lang,
            version, is_deleted,
        ))

        if g != DEFAULT_GRAPH:
            batch.add(self.insert_entity_stmt, (
                collection, g, 'G', p, otype, s, o, g, dtype, lang,
                version, is_deleted,
            ))

        batch.add(self.insert_collection_stmt, (
            collection, g, s, p, o, otype, dtype, lang,
            version, is_deleted,
        ))

        self.session.execute(batch)

    # ========================================================================
    # Query methods
    # g=None means all graphs, g='' means default graph, g='uri' specific
    # version=None means current (latest), version=N means at version N
    # ========================================================================

    @staticmethod
    def _resolve_versioned(rows, version=None):
        """
        Deduplicate rows by quad identity, respecting version ordering.

        Rows arrive sorted by version DESC within each quad (same clustering
        prefix).  For each unique quad, take the first row whose version <= target.
        Skip quads where that row has is_deleted=true.
        """
        seen = set()
        results = []
        for row in rows:
            quad_key = (row.s, row.p, row.o, row.g, row.otype, row.dtype, row.lang)
            if quad_key in seen:
                continue
            if version is not None and row.version > version:
                continue
            seen.add(quad_key)
            if row.is_deleted:
                continue
            results.append(row)
        return results

    @staticmethod
    def _make_manifest_resolver(version=None):
        """
        Stateful row_filter for scanning quads_by_collection.

        Rows arrive clustered by (g, s, p, o, otype, dtype, lang, version DESC),
        so all versions of a given quad are contiguous.  For each unique quad
        prefix, keep the first row with version <= target; skip the quad entirely
        if that row is a deletion marker.
        """
        state = {"prefix": None, "resolved": False}

        def accept(row):
            prefix = (row.g, row.s, row.p, row.o,
                      row.otype, row.dtype, row.lang)
            if prefix != state["prefix"]:
                state["prefix"] = prefix
                state["resolved"] = False
            if state["resolved"]:
                return False
            if version is not None and row.version > version:
                return False
            state["resolved"] = True
            return not row.is_deleted

        return accept

    @staticmethod
    def _make_entity_resolver(version=None, g=None):
        """
        Stateful row_filter for scanning quads_by_entity.

        Same version-resolution logic as _make_manifest_resolver, with an
        optional graph filter folded in so that the caller's limit counts
        only fully-resolved, graph-matched quads.
        """
        state = {"prefix": None, "resolved": False}

        def accept(row):
            prefix = (row.g, row.s, row.p, row.o,
                      row.otype, row.dtype, row.lang)
            if prefix != state["prefix"]:
                state["prefix"] = prefix
                state["resolved"] = False
            if state["resolved"]:
                return False
            if version is not None and row.version > version:
                return False
            state["resolved"] = True
            if row.is_deleted:
                return False
            if g is not None and row.g != g:
                return False
            return True

        return accept

    def _scan_manifest(self, collection, g=None, version=None,
                       limit=None, fetch_size=5000):
        """Sync manifest scan with in-process version resolution."""
        if g is not None:
            cql = (
                f"SELECT g, s, p, o, otype, dtype, lang, version, is_deleted "
                f"FROM {self.collection_table} "
                "WHERE collection = %s AND g = %s"
            )
            params = (collection, g)
        else:
            cql = (
                f"SELECT g, s, p, o, otype, dtype, lang, version, is_deleted "
                f"FROM {self.collection_table} "
                "WHERE collection = %s"
            )
            params = (collection,)

        stmt = SimpleStatement(cql, fetch_size=fetch_size)
        accept = self._make_manifest_resolver(version)
        results = []
        for row in self.session.execute(stmt, params):
            if not accept(row):
                continue
            results.append(QuadResult(
                s=row.s, p=row.p, o=row.o, g=row.g,
                otype=row.otype, dtype=row.dtype, lang=row.lang,
            ))
            if limit and len(results) >= limit:
                break
        return results

    async def _async_scan_manifest(self, collection, g=None, version=None,
                                   limit=None, fetch_size=5000):
        """Async manifest scan with in-process version resolution."""
        if g is not None:
            cql = (
                f"SELECT g, s, p, o, otype, dtype, lang, version, is_deleted "
                f"FROM {self.collection_table} "
                "WHERE collection = %s AND g = %s"
            )
            params = (collection, g)
        else:
            cql = (
                f"SELECT g, s, p, o, otype, dtype, lang, version, is_deleted "
                f"FROM {self.collection_table} "
                "WHERE collection = %s"
            )
            params = (collection,)

        accept = self._make_manifest_resolver(version)
        rows = await async_scan(
            self.session, cql, params,
            row_filter=accept, limit=limit, fetch_size=fetch_size,
        )
        return [
            QuadResult(
                s=row.s, p=row.p, o=row.o, g=row.g,
                otype=row.otype, dtype=row.dtype, lang=row.lang,
            )
            for row in rows
        ]

    async def async_stream_manifest(self, collection, g=None, version=None,
                                    limit=None, batch_size=20,
                                    fetch_size=5000):
        """
        Yield QuadResult batches from quads_by_collection as pages arrive.

        Uses the sync driver's page iteration from inside the asyncio loop
        via ``run_in_executor``; applies version resolution across page
        boundaries using a single stateful filter.
        """
        if g is not None:
            cql = (
                f"SELECT g, s, p, o, otype, dtype, lang, version, is_deleted "
                f"FROM {self.collection_table} "
                "WHERE collection = %s AND g = %s"
            )
            params = (collection, g)
        else:
            cql = (
                f"SELECT g, s, p, o, otype, dtype, lang, version, is_deleted "
                f"FROM {self.collection_table} "
                "WHERE collection = %s"
            )
            params = (collection,)

        stmt = SimpleStatement(cql, fetch_size=fetch_size)
        accept = self._make_manifest_resolver(version)
        loop = asyncio.get_running_loop()

        result_set = await loop.run_in_executor(
            None, lambda: self.session.execute(stmt, params)
        )

        batch = []
        emitted = 0

        while True:
            for row in result_set.current_rows:
                if not accept(row):
                    continue
                batch.append(QuadResult(
                    s=row.s, p=row.p, o=row.o, g=row.g,
                    otype=row.otype, dtype=row.dtype, lang=row.lang,
                ))
                emitted += 1
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
                if limit and emitted >= limit:
                    if batch:
                        yield batch
                    return
            if not result_set.has_more_pages:
                break
            await loop.run_in_executor(None, result_set.fetch_next_page)

        if batch:
            yield batch

    def get_all(self, collection, g=None, version=None, limit=50):
        return self._scan_manifest(
            collection, g=g, version=version, limit=limit,
        )

    def _scan_entity(self, stmt, params, version=None, g=None,
                     limit=None, extra_filter=None, fetch_size=5000):
        """Sync entity scan with in-process version resolution."""
        stmt.fetch_size = fetch_size
        accept = self._make_entity_resolver(version, g)
        results = []
        for row in self.session.execute(stmt, params):
            if not accept(row):
                continue
            if extra_filter and not extra_filter(row):
                continue
            results.append(QuadResult(
                s=row.s, p=row.p, o=row.o, g=row.g,
                otype=row.otype, dtype=row.dtype, lang=row.lang,
            ))
            if limit and len(results) >= limit:
                break
        return results

    def get_s(self, collection, s, g=None, version=None, limit=10):
        return self._scan_entity(
            self.get_entity_as_s_stmt, (collection, s),
            version=version, g=g, limit=limit,
        )

    def get_p(self, collection, p, g=None, version=None, limit=10):
        return self._scan_entity(
            self.get_entity_as_p_stmt, (collection, p),
            version=version, g=g, limit=limit,
        )

    def get_o(self, collection, o, g=None, version=None, limit=10):
        return self._scan_entity(
            self.get_entity_as_o_stmt, (collection, o),
            version=version, g=g, limit=limit,
        )

    def get_sp(self, collection, s, p, g=None, version=None, limit=10):
        return self._scan_entity(
            self.get_entity_as_s_p_stmt, (collection, s, p),
            version=version, g=g, limit=limit,
        )

    def get_po(self, collection, p, o, g=None, version=None, limit=10):
        return self._scan_entity(
            self.get_entity_as_o_p_stmt, (collection, o, p),
            version=version, g=g, limit=limit,
        )

    def get_os(self, collection, o, s, g=None, version=None, limit=10):
        return self._scan_entity(
            self.get_entity_as_s_stmt, (collection, s),
            version=version, g=g, limit=limit,
            extra_filter=lambda row: row.o == o,
        )

    def get_spo(self, collection, s, p, o, g=None, version=None, limit=10):
        return self._scan_entity(
            self.get_entity_as_s_p_stmt, (collection, s, p),
            version=version, g=g, limit=limit,
            extra_filter=lambda row: row.o == o,
        )

    def get_g(self, collection, g, version=None, limit=50):
        if g is None:
            g = DEFAULT_GRAPH
        return self._scan_manifest(
            collection, g=g, version=version, limit=limit,
        )

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
            self.session.execute(
                f"INSERT INTO {self.collection_metadata_table} (collection, created_at) VALUES (%s, %s)",
                (collection, datetime.datetime.now())
            )
            logger.info(f"Created collection metadata for {collection}")
        except Exception as e:
            logger.error(f"Error creating collection: {e}")
            raise e

    def delete_collection(self, collection):
        rows = self.session.execute(
            f"SELECT g, s, p, o, otype, dtype, lang FROM {self.collection_table} WHERE collection = %s",
            (collection,)
        )

        entities = set()
        # Versioned manifest has one row per write event; dedupe so each quad
        # gets exactly one DELETE (the delete covers all versions via the
        # partial-clustering-key delete on quads_by_collection).
        quads = set()

        for row in rows:
            g, s, p, o = row.g, row.s, row.p, row.o
            otype = row.otype
            dtype = row.dtype if hasattr(row, 'dtype') else ''
            lang = row.lang if hasattr(row, 'lang') else ''
            quads.add((g, s, p, o, otype, dtype, lang))

            entities.add(s)
            entities.add(p)
            entities.add(o)

            if g != DEFAULT_GRAPH:
                entities.add(g)

        batch = BatchStatement()
        count = 0

        for entity in entities:
            batch.add(self.delete_entity_partition_stmt, (collection, entity))
            count += 1
            if count % 50 == 0:
                self.session.execute(batch)
                batch = BatchStatement()

        if count % 50 != 0:
            self.session.execute(batch)

        batch = BatchStatement()
        count = 0

        for g, s, p, o, otype, dtype, lang in quads:
            batch.add(self.delete_collection_row_stmt, (collection, g, s, p, o, otype, dtype, lang))
            count += 1
            if count % 50 == 0:
                self.session.execute(batch)
                batch = BatchStatement()

        if count % 50 != 0:
            self.session.execute(batch)

        self.session.execute(
            f"DELETE FROM {self.collection_metadata_table} WHERE collection = %s",
            (collection,)
        )

        logger.info(f"Deleted collection {collection}: {len(entities)} entity partitions, {len(quads)} quads")

    # ========================================================================
    # Async methods — use cassandra driver's native async API via async_execute
    # ========================================================================

    async def async_insert(self, collection, s, p, o, g, version, is_deleted,
                           otype, dtype="", lang=""):
        if g is None:
            g = DEFAULT_GRAPH

        batch = BatchStatement()
        batch.add(self.insert_entity_stmt, (
            collection, s, 'S', p, otype, s, o, g, dtype, lang,
            version, is_deleted,
        ))
        batch.add(self.insert_entity_stmt, (
            collection, p, 'P', p, otype, s, o, g, dtype, lang,
            version, is_deleted,
        ))
        batch.add(self.insert_entity_stmt, (
            collection, o, 'O', p, otype, s, o, g, dtype, lang,
            version, is_deleted,
        ))
        if g != DEFAULT_GRAPH:
            batch.add(self.insert_entity_stmt, (
                collection, g, 'G', p, otype, s, o, g, dtype, lang,
                version, is_deleted,
            ))

        batch.add(self.insert_collection_stmt, (
            collection, g, s, p, o, otype, dtype, lang,
            version, is_deleted,
        ))

        await async_execute(self.session, batch)

    async def async_get_all(self, collection, g=None, version=None, limit=50):
        return await self._async_scan_manifest(
            collection, g=g, version=version, limit=limit,
        )

    async def _async_scan_entity(self, stmt, params, version=None, g=None,
                                limit=None, extra_filter=None,
                                fetch_size=5000):
        """Async entity scan with in-process version resolution."""
        def combined_filter(row):
            if not accept(row):
                return False
            if extra_filter and not extra_filter(row):
                return False
            return True

        accept = self._make_entity_resolver(version, g)
        rows = await async_scan(
            self.session, stmt, params,
            row_filter=combined_filter, limit=limit, fetch_size=fetch_size,
        )
        return [
            QuadResult(
                s=row.s, p=row.p, o=row.o, g=row.g,
                otype=row.otype, dtype=row.dtype, lang=row.lang,
            )
            for row in rows
        ]

    async def async_get_s(self, collection, s, g=None, version=None, limit=10):
        return await self._async_scan_entity(
            self.get_entity_as_s_stmt, (collection, s),
            version=version, g=g, limit=limit,
        )

    async def async_get_p(self, collection, p, g=None, version=None, limit=10):
        return await self._async_scan_entity(
            self.get_entity_as_p_stmt, (collection, p),
            version=version, g=g, limit=limit,
        )

    async def async_get_o(self, collection, o, g=None, version=None, limit=10):
        return await self._async_scan_entity(
            self.get_entity_as_o_stmt, (collection, o),
            version=version, g=g, limit=limit,
        )

    async def async_get_sp(self, collection, s, p, g=None, version=None, limit=10):
        return await self._async_scan_entity(
            self.get_entity_as_s_p_stmt, (collection, s, p),
            version=version, g=g, limit=limit,
        )

    async def async_get_po(self, collection, p, o, g=None, version=None, limit=10):
        return await self._async_scan_entity(
            self.get_entity_as_o_p_stmt, (collection, o, p),
            version=version, g=g, limit=limit,
        )

    async def async_get_os(self, collection, o, s, g=None, version=None, limit=10):
        return await self._async_scan_entity(
            self.get_entity_as_s_stmt, (collection, s),
            version=version, g=g, limit=limit,
            extra_filter=lambda row: row.o == o,
        )

    async def async_get_spo(self, collection, s, p, o, g=None, version=None, limit=10):
        return await self._async_scan_entity(
            self.get_entity_as_s_p_stmt, (collection, s, p),
            version=version, g=g, limit=limit,
            extra_filter=lambda row: row.o == o,
        )

    async def async_get_g(self, collection, g, version=None, limit=50):
        if g is None:
            g = DEFAULT_GRAPH
        return await self._async_scan_manifest(
            collection, g=g, version=version, limit=limit,
        )

    async def async_collection_exists(self, collection):
        try:
            result = await async_execute(
                self.session,
                f"SELECT collection FROM {self.collection_metadata_table} WHERE collection = %s LIMIT 1",
                (collection,)
            )
            return bool(result)
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False

    async def async_create_collection(self, collection):
        await async_execute(
            self.session,
            f"INSERT INTO {self.collection_metadata_table} (collection, created_at) VALUES (%s, %s)",
            (collection, datetime.datetime.now())
        )
        logger.info(f"Created collection metadata for {collection}")

    async def async_delete_collection(self, collection):
        rows = await async_scan(
            self.session,
            f"SELECT g, s, p, o, otype, dtype, lang FROM {self.collection_table} WHERE collection = %s",
            (collection,)
        )

        entities = set()
        # Dedupe: versioned manifest has one row per write event.
        quads = set()
        for row in rows:
            g, s, p, o = row.g, row.s, row.p, row.o
            otype = row.otype
            dtype = row.dtype if hasattr(row, 'dtype') else ''
            lang = row.lang if hasattr(row, 'lang') else ''
            quads.add((g, s, p, o, otype, dtype, lang))
            entities.add(s)
            entities.add(p)
            entities.add(o)
            if g != DEFAULT_GRAPH:
                entities.add(g)

        batch = BatchStatement()
        count = 0
        for entity in entities:
            batch.add(self.delete_entity_partition_stmt, (collection, entity))
            count += 1
            if count % 50 == 0:
                await async_execute(self.session, batch)
                batch = BatchStatement()
        if count % 50 != 0:
            await async_execute(self.session, batch)

        batch = BatchStatement()
        count = 0
        for g, s, p, o, otype, dtype, lang in quads:
            batch.add(self.delete_collection_row_stmt, (collection, g, s, p, o, otype, dtype, lang))
            count += 1
            if count % 50 == 0:
                await async_execute(self.session, batch)
                batch = BatchStatement()
        if count % 50 != 0:
            await async_execute(self.session, batch)

        await async_execute(
            self.session,
            f"DELETE FROM {self.collection_metadata_table} WHERE collection = %s",
            (collection,)
        )
        logger.info(f"Deleted collection {collection}: {len(entities)} entity partitions, {len(quads)} quads")

    # ========================================================================
    # Version management
    # ========================================================================

    def get_graph_version(self, collection, named_graph):
        rows = self.session.execute(
            self.get_graph_version_stmt, (collection, named_graph)
        )
        row = rows.one()
        return row.current_version if row else None

    def get_version_map(self, collection):
        rows = self.session.execute(
            self.get_version_map_stmt, (collection,)
        )
        return {row.named_graph: row.current_version for row in rows}

    def bootstrap_graph_version(self, collection, named_graph):
        existing = self.get_graph_version(collection, named_graph)
        if existing is not None:
            return existing

        self.session.execute(
            self.set_graph_version_stmt, (collection, named_graph, 1)
        )
        self.session.execute(
            self.insert_version_log_stmt,
            (collection, named_graph, 1, datetime.datetime.now(), "")
        )
        logger.info(
            f"Bootstrapped version for {collection}/{named_graph} at v1"
        )
        return 1

    def bump_graph_version(self, collection, named_graph, description=""):
        current = self.bootstrap_graph_version(collection, named_graph)
        new_version = current + 1

        self.session.execute(
            self.set_graph_version_stmt, (collection, named_graph, new_version)
        )
        self.session.execute(
            self.insert_version_log_stmt,
            (collection, named_graph, new_version, datetime.datetime.now(),
             description)
        )
        logger.info(
            f"Bumped version for {collection}/{named_graph}: "
            f"v{current} -> v{new_version}"
        )
        return new_version

    def get_version_log(self, collection, named_graph):
        rows = self.session.execute(
            self.get_version_log_stmt, (collection, named_graph)
        )
        return [
            {
                "version": row.version,
                "created_at": row.created_at,
                "names": row.names,
                "description": row.description,
            }
            for row in rows
        ]

    async def async_get_graph_version(self, collection, named_graph):
        rows = await async_execute(
            self.session, self.get_graph_version_stmt,
            (collection, named_graph)
        )
        return rows[0].current_version if rows else None

    async def async_get_version_map(self, collection):
        rows = await async_execute(
            self.session, self.get_version_map_stmt, (collection,)
        )
        return {row.named_graph: row.current_version for row in rows}

    async def async_bootstrap_graph_version(self, collection, named_graph):
        existing = await self.async_get_graph_version(collection, named_graph)
        if existing is not None:
            return existing

        await async_execute(
            self.session, self.set_graph_version_stmt,
            (collection, named_graph, 1)
        )
        await async_execute(
            self.session, self.insert_version_log_stmt,
            (collection, named_graph, 1, datetime.datetime.now(), "")
        )
        logger.info(
            f"Bootstrapped version for {collection}/{named_graph} at v1"
        )
        return 1

    async def async_bump_graph_version(self, collection, named_graph,
                                       description=""):
        current = await self.async_bootstrap_graph_version(
            collection, named_graph
        )
        new_version = current + 1

        await async_execute(
            self.session, self.set_graph_version_stmt,
            (collection, named_graph, new_version)
        )
        await async_execute(
            self.session, self.insert_version_log_stmt,
            (collection, named_graph, new_version, datetime.datetime.now(),
             description)
        )
        logger.info(
            f"Bumped version for {collection}/{named_graph}: "
            f"v{current} -> v{new_version}"
        )
        return new_version

    async def async_get_version_log(self, collection, named_graph):
        rows = await async_execute(
            self.session, self.get_version_log_stmt,
            (collection, named_graph)
        )
        return [
            {
                "version": row.version,
                "created_at": row.created_at,
                "names": row.names,
                "description": row.description,
            }
            for row in rows
        ]

    # ========================================================================
    # Version label, diff, revert
    # ========================================================================

    def label_version(self, collection, named_graph, version, name):
        self.session.execute(
            self.add_version_label_stmt,
            ({name}, collection, named_graph, version)
        )

    async def async_label_version(self, collection, named_graph, version, name):
        await async_execute(
            self.session, self.add_version_label_stmt,
            ({name}, collection, named_graph, version)
        )

    def describe_version(self, collection, named_graph, version, description):
        self.session.execute(
            self.set_version_description_stmt,
            (description, collection, named_graph, version)
        )

    async def async_describe_version(self, collection, named_graph, version,
                                     description):
        await async_execute(
            self.session, self.set_version_description_stmt,
            (description, collection, named_graph, version)
        )

    def _get_quads_at_version(self, collection, named_graph, version):
        """Get all live quads in a named graph at a specific version."""
        results = self._scan_manifest(
            collection, g=named_graph, version=version,
        )
        return set(
            (r.s, r.p, r.o, r.g, r.otype, r.dtype, r.lang)
            for r in results
        )

    async def async_get_quads_at_version(self, collection, named_graph, version):
        """Get all live quads in a named graph at a specific version."""
        results = await self._async_scan_manifest(
            collection, g=named_graph, version=version,
        )
        return set(
            (r.s, r.p, r.o, r.g, r.otype, r.dtype, r.lang)
            for r in results
        )

    def diff_versions(self, collection, named_graph, v1, v2):
        """Return (added, removed) quad tuples between versions v1 and v2."""
        quads_v1 = self._get_quads_at_version(collection, named_graph, v1)
        quads_v2 = self._get_quads_at_version(collection, named_graph, v2)
        return quads_v2 - quads_v1, quads_v1 - quads_v2

    async def async_diff_versions(self, collection, named_graph, v1, v2):
        """Return (added, removed) quad tuples between versions v1 and v2."""
        quads_v1 = await self.async_get_quads_at_version(
            collection, named_graph, v1
        )
        quads_v2 = await self.async_get_quads_at_version(
            collection, named_graph, v2
        )
        return quads_v2 - quads_v1, quads_v1 - quads_v2

    def revert_to_version(self, collection, named_graph, target_version):
        """Revert a named graph to a previous version. Non-destructive."""
        current = self.bootstrap_graph_version(collection, named_graph)
        quads_target = self._get_quads_at_version(
            collection, named_graph, target_version
        )
        quads_current = self._get_quads_at_version(
            collection, named_graph, current
        )

        new_version = self.bump_graph_version(collection, named_graph)

        for s, p, o, g, otype, dtype, lang in quads_target - quads_current:
            self.insert(collection, s, p, o, g, new_version, False,
                        otype, dtype, lang)

        for s, p, o, g, otype, dtype, lang in quads_current - quads_target:
            self.insert(collection, s, p, o, g, new_version, True,
                        otype, dtype, lang)

        return new_version

    async def async_revert_to_version(self, collection, named_graph,
                                      target_version):
        """Revert a named graph to a previous version. Non-destructive."""
        current = await self.async_bootstrap_graph_version(
            collection, named_graph
        )
        quads_target = await self.async_get_quads_at_version(
            collection, named_graph, target_version
        )
        quads_current = await self.async_get_quads_at_version(
            collection, named_graph, current
        )

        new_version = await self.async_bump_graph_version(
            collection, named_graph
        )

        for s, p, o, g, otype, dtype, lang in quads_target - quads_current:
            await self.async_insert(
                collection, s, p, o, g, new_version, False,
                otype, dtype, lang
            )

        for s, p, o, g, otype, dtype, lang in quads_current - quads_target:
            await self.async_insert(
                collection, s, p, o, g, new_version, True,
                otype, dtype, lang
            )

        return new_version

    # ========================================================================
    # Purge — drop version history before a cutoff
    # ========================================================================

    async def async_purge_graph(self, collection, named_graph, before_version):
        """
        Remove version history before ``before_version`` for a named graph.

        For each unique quad, the latest entry with version < before_version
        is kept (it establishes the state at the cutoff), older entries are
        deleted.  Dead-end delete markers (no entries >= before_version) are
        removed entirely.  Version log entries before the cutoff are also
        deleted.
        """
        cql = (
            f"SELECT g, s, p, o, otype, dtype, lang, version, is_deleted "
            f"FROM {self.collection_table} "
            "WHERE collection = %s AND g = %s"
        )
        stmt = SimpleStatement(cql, fetch_size=5000)

        rows = await async_scan(
            self.session, stmt, (collection, named_graph),
        )

        quads = {}
        for row in rows:
            key = (row.g, row.s, row.p, row.o, row.otype, row.dtype, row.lang)
            quads.setdefault(key, []).append(
                (row.version, row.is_deleted)
            )

        to_delete = []

        for key, entries in quads.items():
            entries.sort(key=lambda e: e[0], reverse=True)

            has_post_cutoff = any(v >= before_version for v, _ in entries)
            pre_cutoff = [(v, d) for v, d in entries if v < before_version]

            if not pre_cutoff:
                continue

            keep_version = pre_cutoff[0][0]
            keep_is_deleted = pre_cutoff[0][1]

            if keep_is_deleted and not has_post_cutoff:
                for v, _ in pre_cutoff:
                    to_delete.append((key, v))
            else:
                for v, _ in pre_cutoff[1:]:
                    to_delete.append((key, v))

        batch = BatchStatement()
        count = 0

        for (g, s, p, o, otype, dtype, lang), version in to_delete:
            batch.add(self.delete_collection_version_stmt,
                      (collection, g, s, p, o, otype, dtype, lang, version))

            for entity, role in [(s, 'S'), (p, 'P'), (o, 'O')]:
                batch.add(self.delete_entity_version_stmt,
                          (collection, entity, role,
                           p, otype, s, o, g, dtype, lang, version))

            if g != DEFAULT_GRAPH:
                batch.add(self.delete_entity_version_stmt,
                          (collection, g, 'G',
                           p, otype, s, o, g, dtype, lang, version))

            count += 1
            if count % 10 == 0:
                await async_execute(self.session, batch)
                batch = BatchStatement()

        if count % 10 != 0:
            await async_execute(self.session, batch)

        log = await self.async_get_version_log(collection, named_graph)
        log_batch = BatchStatement()
        log_count = 0
        for entry in log:
            if entry["version"] < before_version:
                log_batch.add(self.delete_version_log_stmt,
                              (collection, named_graph, entry["version"]))
                log_count += 1
                if log_count % 50 == 0:
                    await async_execute(self.session, log_batch)
                    log_batch = BatchStatement()
        if log_count % 50 != 0:
            await async_execute(self.session, log_batch)

        logger.info(
            f"Purged {collection}/{named_graph}: "
            f"{count} quad versions, {log_count} log entries removed "
            f"(before v{before_version})"
        )

        return count

    def close(self):
        if hasattr(self, 'session') and self.session:
            self.session.shutdown()
        if hasattr(self, 'cluster') and self.cluster:
            self.cluster.shutdown()
            if self.cluster in _active_clusters:
                _active_clusters.remove(self.cluster)


class QuadResult:
    """
    Result object for quad queries, including object type metadata.

    Attributes:
        s: Subject value
        p: Predicate value
        o: Object value
        g: Graph/dataset value
        otype: Object type - 'u' (URI), 'l' (literal), 't' (triple)
        dtype: XSD datatype (for literals)
        lang: Language tag (for literals)
    """

    def __init__(self, s, p, o, g, otype='u', dtype='', lang=''):
        self.s = s
        self.p = p
        self.o = o
        self.g = g
        self.otype = otype
        self.dtype = dtype
        self.lang = lang


