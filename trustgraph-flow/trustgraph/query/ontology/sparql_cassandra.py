"""
SPARQL-Cassandra engine using Python rdflib.
Executes SPARQL queries against Cassandra using a custom Store implementation.
"""

import logging
from typing import Dict, Any, List, Optional, Iterator, Tuple
from dataclasses import dataclass
import json

# Try to import rdflib
try:
    from rdflib import Graph, Namespace, URIRef, Literal, BNode
    from rdflib.store import Store
    from rdflib.plugins.sparql.processor import SPARQLResult
    from rdflib.plugins.sparql import prepareQuery
    from rdflib.term import Node
    RDFLIB_AVAILABLE = True
except ImportError:
    RDFLIB_AVAILABLE = False

# Try to import Cassandra driver
try:
    from cassandra.cluster import Cluster
    from cassandra.auth import PlainTextAuthProvider
    from cassandra.policies import DCAwareRoundRobinPolicy
    CASSANDRA_AVAILABLE = True
except ImportError:
    CASSANDRA_AVAILABLE = False

from ....tables.config import ConfigTableStore

logger = logging.getLogger(__name__)


@dataclass
class SPARQLResult:
    """Result from SPARQL query execution."""
    bindings: List[Dict[str, Any]]
    variables: List[str]
    ask_result: Optional[bool] = None  # For ASK queries
    execution_time: float = 0.0
    query_plan: Optional[str] = None


class CassandraTripleStore(Store if RDFLIB_AVAILABLE else object):
    """Custom rdflib Store implementation for Cassandra."""

    def __init__(self, cassandra_config: Dict[str, Any]):
        """Initialize Cassandra triple store.

        Args:
            cassandra_config: Cassandra connection configuration
        """
        if not CASSANDRA_AVAILABLE:
            raise RuntimeError("Cassandra driver not available")
        if not RDFLIB_AVAILABLE:
            raise RuntimeError("rdflib not available")

        super().__init__()

        self.cassandra_config = cassandra_config
        self.cluster = None
        self.session = None
        self.keyspace = cassandra_config.get('keyspace', 'trustgraph')

        # Triple storage table structure
        self.triple_table = f"{self.keyspace}.triples"
        self.metadata_table = f"{self.keyspace}.triple_metadata"

    def open(self, configuration=None, create=False):
        """Open connection to Cassandra."""
        try:
            # Create authentication if provided
            auth_provider = None
            if 'username' in self.cassandra_config and 'password' in self.cassandra_config:
                auth_provider = PlainTextAuthProvider(
                    username=self.cassandra_config['username'],
                    password=self.cassandra_config['password']
                )

            # Create cluster
            self.cluster = Cluster(
                [self.cassandra_config.get('host', 'localhost')],
                port=self.cassandra_config.get('port', 9042),
                auth_provider=auth_provider,
                load_balancing_policy=DCAwareRoundRobinPolicy()
            )

            # Connect
            self.session = self.cluster.connect()

            # Ensure keyspace exists
            if create:
                self._create_schema()

            # Set keyspace
            self.session.set_keyspace(self.keyspace)

            logger.info(f"Connected to Cassandra cluster: {self.cassandra_config.get('host')}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to Cassandra: {e}")
            return False

    def close(self, commit_pending_transaction=True):
        """Close Cassandra connection."""
        if self.session:
            self.session.shutdown()
        if self.cluster:
            self.cluster.shutdown()

    def _create_schema(self):
        """Create Cassandra schema for triple storage."""
        # Create keyspace
        self.session.execute(f"""
            CREATE KEYSPACE IF NOT EXISTS {self.keyspace}
            WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
        """)

        # Create triples table optimized for SPARQL queries
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.triple_table} (
                subject text,
                predicate text,
                object text,
                object_datatype text,
                object_language text,
                is_literal boolean,
                graph_id text,
                PRIMARY KEY ((subject), predicate, object)
            )
        """)

        # Create indexes for efficient querying
        self.session.execute(f"""
            CREATE INDEX IF NOT EXISTS ON {self.triple_table} (predicate)
        """)
        self.session.execute(f"""
            CREATE INDEX IF NOT EXISTS ON {self.triple_table} (object)
        """)

        # Metadata table for graph information
        self.session.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.metadata_table} (
                graph_id text PRIMARY KEY,
                created timestamp,
                modified timestamp,
                triple_count counter
            )
        """)

    def triples(self, triple_pattern, context=None):
        """Retrieve triples matching the given pattern.

        Args:
            triple_pattern: (subject, predicate, object) pattern with None for variables
            context: Graph context (optional)

        Yields:
            Matching triples as (subject, predicate, object) tuples
        """
        if not self.session:
            return

        subject, predicate, object_val = triple_pattern

        # Build CQL query based on pattern
        cql_queries = self._pattern_to_cql(subject, predicate, object_val)

        for cql, params in cql_queries:
            try:
                rows = self.session.execute(cql, params)
                for row in rows:
                    yield self._row_to_triple(row)
            except Exception as e:
                logger.error(f"Error executing CQL query: {e}")

    def _pattern_to_cql(self, subject, predicate, object_val) -> List[Tuple[str, List]]:
        """Convert triple pattern to CQL queries.

        Args:
            subject: Subject node or None
            predicate: Predicate node or None
            object_val: Object node or None

        Returns:
            List of (CQL query, parameters) tuples
        """
        queries = []

        # Convert None to wildcard, nodes to strings
        s_str = str(subject) if subject else None
        p_str = str(predicate) if predicate else None
        o_str = str(object_val) if object_val else None

        if s_str and p_str and o_str:
            # Specific triple lookup
            cql = f"SELECT * FROM {self.triple_table} WHERE subject = ? AND predicate = ? AND object = ?"
            queries.append((cql, [s_str, p_str, o_str]))

        elif s_str and p_str:
            # Subject and predicate known
            cql = f"SELECT * FROM {self.triple_table} WHERE subject = ? AND predicate = ?"
            queries.append((cql, [s_str, p_str]))

        elif s_str:
            # Subject known
            cql = f"SELECT * FROM {self.triple_table} WHERE subject = ?"
            queries.append((cql, [s_str]))

        elif p_str:
            # Predicate known (requires index scan)
            cql = f"SELECT * FROM {self.triple_table} WHERE predicate = ? ALLOW FILTERING"
            queries.append((cql, [p_str]))

        elif o_str:
            # Object known (requires index scan)
            cql = f"SELECT * FROM {self.triple_table} WHERE object = ? ALLOW FILTERING"
            queries.append((cql, [o_str]))

        else:
            # Full scan (should be avoided in production)
            cql = f"SELECT * FROM {self.triple_table}"
            queries.append((cql, []))

        return queries

    def _row_to_triple(self, row):
        """Convert Cassandra row to RDF triple.

        Args:
            row: Cassandra row object

        Returns:
            (subject, predicate, object) tuple with rdflib nodes
        """
        # Convert to rdflib nodes
        subject = URIRef(row.subject) if row.subject.startswith('http') else BNode(row.subject)

        predicate = URIRef(row.predicate)

        if row.is_literal:
            # Create literal with datatype/language
            if row.object_datatype:
                object_node = Literal(row.object, datatype=URIRef(row.object_datatype))
            elif row.object_language:
                object_node = Literal(row.object, lang=row.object_language)
            else:
                object_node = Literal(row.object)
        else:
            object_node = URIRef(row.object) if row.object.startswith('http') else BNode(row.object)

        return (subject, predicate, object_node)

    def add(self, triple, context=None, quoted=False):
        """Add a triple to the store.

        Args:
            triple: (subject, predicate, object) tuple
            context: Graph context
            quoted: Whether triple is quoted
        """
        if not self.session:
            return

        subject, predicate, object_val = triple

        # Convert to storage format
        s_str = str(subject)
        p_str = str(predicate)

        is_literal = isinstance(object_val, Literal)
        o_str = str(object_val)
        o_datatype = str(object_val.datatype) if is_literal and object_val.datatype else None
        o_language = object_val.language if is_literal and object_val.language else None

        # Insert into Cassandra
        cql = f"""
            INSERT INTO {self.triple_table}
            (subject, predicate, object, object_datatype, object_language, is_literal, graph_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        try:
            self.session.execute(cql, [
                s_str, p_str, o_str, o_datatype, o_language, is_literal,
                str(context) if context else 'default'
            ])
        except Exception as e:
            logger.error(f"Error adding triple: {e}")

    def remove(self, triple, context=None):
        """Remove a triple from the store.

        Args:
            triple: (subject, predicate, object) tuple
            context: Graph context
        """
        if not self.session:
            return

        subject, predicate, object_val = triple

        cql = f"""
            DELETE FROM {self.triple_table}
            WHERE subject = ? AND predicate = ? AND object = ?
        """

        try:
            self.session.execute(cql, [str(subject), str(predicate), str(object_val)])
        except Exception as e:
            logger.error(f"Error removing triple: {e}")

    def __len__(self, context=None):
        """Get number of triples in store.

        Args:
            context: Graph context

        Returns:
            Number of triples
        """
        if not self.session:
            return 0

        try:
            cql = f"SELECT COUNT(*) FROM {self.triple_table}"
            result = self.session.execute(cql)
            return result.one().count
        except Exception as e:
            logger.error(f"Error counting triples: {e}")
            return 0


class SPARQLCassandraEngine:
    """SPARQL processor using Cassandra backend."""

    def __init__(self, cassandra_config: Dict[str, Any]):
        """Initialize SPARQL-Cassandra engine.

        Args:
            cassandra_config: Cassandra configuration
        """
        if not RDFLIB_AVAILABLE:
            raise RuntimeError("rdflib is required for SPARQL processing")
        if not CASSANDRA_AVAILABLE:
            raise RuntimeError("Cassandra driver is required")

        self.cassandra_config = cassandra_config
        self.store = CassandraTripleStore(cassandra_config)
        self.graph = Graph(store=self.store)

        # Common namespaces
        self.namespaces = {
            'rdf': Namespace('http://www.w3.org/1999/02/22-rdf-syntax-ns#'),
            'rdfs': Namespace('http://www.w3.org/2000/01/rdf-schema#'),
            'owl': Namespace('http://www.w3.org/2002/07/owl#'),
            'xsd': Namespace('http://www.w3.org/2001/XMLSchema#'),
        }

        # Bind namespaces to graph
        for prefix, namespace in self.namespaces.items():
            self.graph.bind(prefix, namespace)

    async def initialize(self, create_schema=False):
        """Initialize the engine.

        Args:
            create_schema: Whether to create Cassandra schema
        """
        success = self.store.open(create=create_schema)
        if not success:
            raise RuntimeError("Failed to connect to Cassandra")

        logger.info("SPARQL-Cassandra engine initialized")

    def execute_sparql(self, sparql_query: str) -> SPARQLResult:
        """Execute SPARQL query against Cassandra.

        Args:
            sparql_query: SPARQL query string

        Returns:
            Query results
        """
        import time
        start_time = time.time()

        try:
            # Prepare and execute query
            prepared_query = prepareQuery(sparql_query)
            result = self.graph.query(prepared_query)

            execution_time = time.time() - start_time

            # Format results based on query type
            if sparql_query.strip().upper().startswith('ASK'):
                return SPARQLResult(
                    bindings=[],
                    variables=[],
                    ask_result=bool(result),
                    execution_time=execution_time
                )
            else:
                # SELECT query
                bindings = []
                variables = result.vars if hasattr(result, 'vars') else []

                for row in result:
                    binding = {}
                    for i, var in enumerate(variables):
                        if i < len(row):
                            value = row[i]
                            binding[str(var)] = self._format_result_value(value)
                    bindings.append(binding)

                return SPARQLResult(
                    bindings=bindings,
                    variables=[str(v) for v in variables],
                    execution_time=execution_time
                )

        except Exception as e:
            logger.error(f"SPARQL execution error: {e}")
            return SPARQLResult(
                bindings=[],
                variables=[],
                execution_time=time.time() - start_time
            )

    def _format_result_value(self, value):
        """Format result value for output.

        Args:
            value: RDF value (URIRef, Literal, BNode)

        Returns:
            Formatted value
        """
        if isinstance(value, URIRef):
            return {'type': 'uri', 'value': str(value)}
        elif isinstance(value, Literal):
            result = {'type': 'literal', 'value': str(value)}
            if value.datatype:
                result['datatype'] = str(value.datatype)
            if value.language:
                result['language'] = value.language
            return result
        elif isinstance(value, BNode):
            return {'type': 'bnode', 'value': str(value)}
        else:
            return {'type': 'unknown', 'value': str(value)}

    def load_triples_from_store(self, config_store: ConfigTableStore):
        """Load triples from TrustGraph's storage into the RDF graph.

        Args:
            config_store: Configuration store with triples
        """
        # This would need to be implemented based on how triples are stored
        # in TrustGraph's Cassandra tables
        logger.info("Loading triples from TrustGraph store...")

        # Example implementation - would need to be adapted
        # to actual TrustGraph storage format
        try:
            # Get all triple data
            # This is a placeholder - actual implementation would need
            # to query the appropriate TrustGraph tables
            pass

        except Exception as e:
            logger.error(f"Error loading triples: {e}")

    def close(self):
        """Close the engine and connections."""
        if self.store:
            self.store.close()
        logger.info("SPARQL-Cassandra engine closed")