"""
Cypher executor for multiple graph databases.
Executes Cypher queries against Neo4j, Memgraph, and FalkorDB.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .cypher_generator import CypherQuery

logger = logging.getLogger(__name__)

# Try to import various database drivers
try:
    from neo4j import GraphDatabase, Driver as Neo4jDriver
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    Neo4jDriver = None

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class CypherResult:
    """Result from Cypher query execution."""
    records: List[Dict[str, Any]]
    summary: Dict[str, Any]
    execution_time: float
    database_type: str
    query_plan: Optional[Dict[str, Any]] = None


class CypherExecutorBase(ABC):
    """Abstract base class for Cypher executors."""

    @abstractmethod
    async def execute(self, cypher_query: CypherQuery) -> CypherResult:
        """Execute Cypher query."""
        pass

    @abstractmethod
    async def close(self):
        """Close database connection."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to database."""
        pass


class Neo4jExecutor(CypherExecutorBase):
    """Cypher executor for Neo4j database."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Neo4j executor.

        Args:
            config: Neo4j configuration
        """
        if not NEO4J_AVAILABLE:
            raise RuntimeError("Neo4j driver not available")

        self.config = config
        self.driver: Optional[Neo4jDriver] = None
        self._connection_pool_size = config.get('connection_pool_size', 10)

    async def connect(self):
        """Connect to Neo4j database."""
        try:
            uri = self.config.get('uri', 'bolt://localhost:7687')
            username = self.config.get('username')
            password = self.config.get('password')

            auth = (username, password) if username and password else None

            # Create driver with connection pool
            self.driver = GraphDatabase.driver(
                uri,
                auth=auth,
                max_connection_pool_size=self._connection_pool_size,
                connection_timeout=self.config.get('connection_timeout', 30),
                max_retry_time=self.config.get('max_retry_time', 15)
            )

            # Verify connectivity
            await asyncio.get_event_loop().run_in_executor(
                None, self.driver.verify_connectivity
            )

            logger.info(f"Connected to Neo4j at {uri}")

        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    async def execute(self, cypher_query: CypherQuery) -> CypherResult:
        """Execute Cypher query against Neo4j.

        Args:
            cypher_query: Cypher query to execute

        Returns:
            Query results
        """
        if not self.driver:
            await self.connect()

        import time
        start_time = time.time()

        try:
            # Execute query in a session
            records = await asyncio.get_event_loop().run_in_executor(
                None, self._execute_sync, cypher_query
            )

            execution_time = time.time() - start_time

            return CypherResult(
                records=records,
                summary={'record_count': len(records)},
                execution_time=execution_time,
                database_type='neo4j'
            )

        except Exception as e:
            logger.error(f"Neo4j query execution error: {e}")
            execution_time = time.time() - start_time
            return CypherResult(
                records=[],
                summary={'error': str(e)},
                execution_time=execution_time,
                database_type='neo4j'
            )

    def _execute_sync(self, cypher_query: CypherQuery) -> List[Dict[str, Any]]:
        """Execute query synchronously in thread executor.

        Args:
            cypher_query: Cypher query to execute

        Returns:
            List of record dictionaries
        """
        with self.driver.session() as session:
            result = session.run(cypher_query.query, cypher_query.parameters)
            records = []
            for record in result:
                record_dict = {}
                for key in record.keys():
                    value = record[key]
                    record_dict[key] = self._format_neo4j_value(value)
                records.append(record_dict)
            return records

    def _format_neo4j_value(self, value):
        """Format Neo4j value for JSON serialization.

        Args:
            value: Neo4j value

        Returns:
            JSON-serializable value
        """
        # Handle Neo4j node objects
        if hasattr(value, 'labels') and hasattr(value, 'items'):
            return {
                'labels': list(value.labels),
                'properties': dict(value.items())
            }
        # Handle Neo4j relationship objects
        elif hasattr(value, 'type') and hasattr(value, 'items'):
            return {
                'type': value.type,
                'properties': dict(value.items())
            }
        # Handle Neo4j path objects
        elif hasattr(value, 'nodes') and hasattr(value, 'relationships'):
            return {
                'nodes': [self._format_neo4j_value(n) for n in value.nodes],
                'relationships': [self._format_neo4j_value(r) for r in value.relationships]
            }
        else:
            return value

    async def close(self):
        """Close Neo4j connection."""
        if self.driver:
            await asyncio.get_event_loop().run_in_executor(
                None, self.driver.close
            )
            self.driver = None
            logger.info("Neo4j connection closed")

    def is_connected(self) -> bool:
        """Check if connected to Neo4j."""
        return self.driver is not None


class MemgraphExecutor(CypherExecutorBase):
    """Cypher executor for Memgraph database."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Memgraph executor.

        Args:
            config: Memgraph configuration
        """
        if not NEO4J_AVAILABLE:  # Memgraph uses Neo4j driver
            raise RuntimeError("Neo4j driver required for Memgraph")

        self.config = config
        self.driver: Optional[Neo4jDriver] = None

    async def connect(self):
        """Connect to Memgraph database."""
        try:
            uri = self.config.get('uri', 'bolt://localhost:7688')
            username = self.config.get('username')
            password = self.config.get('password')

            auth = (username, password) if username and password else None

            # Memgraph uses Neo4j driver but with different defaults
            self.driver = GraphDatabase.driver(
                uri,
                auth=auth,
                max_connection_pool_size=self.config.get('connection_pool_size', 5),
                connection_timeout=self.config.get('connection_timeout', 10)
            )

            # Verify connectivity
            await asyncio.get_event_loop().run_in_executor(
                None, self.driver.verify_connectivity
            )

            logger.info(f"Connected to Memgraph at {uri}")

        except Exception as e:
            logger.error(f"Failed to connect to Memgraph: {e}")
            raise

    async def execute(self, cypher_query: CypherQuery) -> CypherResult:
        """Execute Cypher query against Memgraph.

        Args:
            cypher_query: Cypher query to execute

        Returns:
            Query results
        """
        if not self.driver:
            await self.connect()

        import time
        start_time = time.time()

        try:
            # Execute query with Memgraph-specific optimizations
            records = await asyncio.get_event_loop().run_in_executor(
                None, self._execute_memgraph_sync, cypher_query
            )

            execution_time = time.time() - start_time

            return CypherResult(
                records=records,
                summary={
                    'record_count': len(records),
                    'engine': 'memgraph'
                },
                execution_time=execution_time,
                database_type='memgraph'
            )

        except Exception as e:
            logger.error(f"Memgraph query execution error: {e}")
            execution_time = time.time() - start_time
            return CypherResult(
                records=[],
                summary={'error': str(e)},
                execution_time=execution_time,
                database_type='memgraph'
            )

    def _execute_memgraph_sync(self, cypher_query: CypherQuery) -> List[Dict[str, Any]]:
        """Execute query synchronously for Memgraph.

        Args:
            cypher_query: Cypher query to execute

        Returns:
            List of record dictionaries
        """
        with self.driver.session() as session:
            # Add Memgraph-specific query hints if available
            query = cypher_query.query
            if cypher_query.database_hints and cypher_query.database_hints.get('memory_limit'):
                # Memgraph supports memory limits
                query = f"// Memory limit: {cypher_query.database_hints['memory_limit']}\n{query}"

            result = session.run(query, cypher_query.parameters)
            records = []
            for record in result:
                record_dict = {}
                for key in record.keys():
                    record_dict[key] = record[key]
                records.append(record_dict)
            return records

    async def close(self):
        """Close Memgraph connection."""
        if self.driver:
            await asyncio.get_event_loop().run_in_executor(
                None, self.driver.close
            )
            self.driver = None
            logger.info("Memgraph connection closed")

    def is_connected(self) -> bool:
        """Check if connected to Memgraph."""
        return self.driver is not None


class FalkorDBExecutor(CypherExecutorBase):
    """Cypher executor for FalkorDB (Redis-based graph database)."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize FalkorDB executor.

        Args:
            config: FalkorDB configuration
        """
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis driver required for FalkorDB")

        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self.graph_name = config.get('graph_name', 'knowledge_graph')

    async def connect(self):
        """Connect to FalkorDB (Redis)."""
        try:
            self.redis_client = redis.Redis(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 6379),
                password=self.config.get('password'),
                db=self.config.get('db', 0),
                decode_responses=True,
                socket_connect_timeout=self.config.get('connection_timeout', 10),
                socket_timeout=self.config.get('socket_timeout', 10)
            )

            # Test connection
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis_client.ping
            )

            logger.info(f"Connected to FalkorDB at {self.config.get('host', 'localhost')}")

        except Exception as e:
            logger.error(f"Failed to connect to FalkorDB: {e}")
            raise

    async def execute(self, cypher_query: CypherQuery) -> CypherResult:
        """Execute Cypher query against FalkorDB.

        Args:
            cypher_query: Cypher query to execute

        Returns:
            Query results
        """
        if not self.redis_client:
            await self.connect()

        import time
        start_time = time.time()

        try:
            # Execute query using FalkorDB's GRAPH.QUERY command
            records = await asyncio.get_event_loop().run_in_executor(
                None, self._execute_falkordb_sync, cypher_query
            )

            execution_time = time.time() - start_time

            return CypherResult(
                records=records,
                summary={
                    'record_count': len(records),
                    'engine': 'falkordb'
                },
                execution_time=execution_time,
                database_type='falkordb'
            )

        except Exception as e:
            logger.error(f"FalkorDB query execution error: {e}")
            execution_time = time.time() - start_time
            return CypherResult(
                records=[],
                summary={'error': str(e)},
                execution_time=execution_time,
                database_type='falkordb'
            )

    def _execute_falkordb_sync(self, cypher_query: CypherQuery) -> List[Dict[str, Any]]:
        """Execute query synchronously for FalkorDB.

        Args:
            cypher_query: Cypher query to execute

        Returns:
            List of record dictionaries
        """
        # Substitute parameters in query (FalkorDB parameter handling)
        query = cypher_query.query
        for param, value in cypher_query.parameters.items():
            if isinstance(value, str):
                query = query.replace(f'${param}', f'"{value}"')
            else:
                query = query.replace(f'${param}', str(value))

        # Execute using FalkorDB GRAPH.QUERY command
        result = self.redis_client.execute_command(
            'GRAPH.QUERY', self.graph_name, query
        )

        # Parse FalkorDB result format
        records = []
        if result and len(result) > 1:
            # FalkorDB returns [header, data rows, statistics]
            headers = result[0] if result[0] else []
            data_rows = result[1] if len(result) > 1 else []

            for row in data_rows:
                record = {}
                for i, header in enumerate(headers):
                    if i < len(row):
                        record[header] = self._format_falkordb_value(row[i])
                records.append(record)

        return records

    def _format_falkordb_value(self, value):
        """Format FalkorDB value for JSON serialization.

        Args:
            value: FalkorDB value

        Returns:
            JSON-serializable value
        """
        # FalkorDB returns values in specific formats
        if isinstance(value, list) and len(value) == 3:
            # Check if it's a node/relationship representation
            if value[0] == 1:  # Node
                return {
                    'type': 'node',
                    'labels': value[1],
                    'properties': value[2]
                }
            elif value[0] == 2:  # Relationship
                return {
                    'type': 'relationship',
                    'rel_type': value[1],
                    'properties': value[2]
                }

        return value

    async def close(self):
        """Close FalkorDB connection."""
        if self.redis_client:
            await asyncio.get_event_loop().run_in_executor(
                None, self.redis_client.close
            )
            self.redis_client = None
            logger.info("FalkorDB connection closed")

    def is_connected(self) -> bool:
        """Check if connected to FalkorDB."""
        return self.redis_client is not None


class CypherExecutor:
    """Multi-database Cypher executor with automatic routing."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize multi-database executor.

        Args:
            config: Configuration for all database types
        """
        self.config = config
        self.executors: Dict[str, CypherExecutorBase] = {}

        # Initialize available executors
        self._initialize_executors()

    def _initialize_executors(self):
        """Initialize database executors based on configuration."""
        # Neo4j executor
        if 'neo4j' in self.config and NEO4J_AVAILABLE:
            try:
                self.executors['neo4j'] = Neo4jExecutor(self.config['neo4j'])
                logger.info("Neo4j executor initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Neo4j executor: {e}")

        # Memgraph executor
        if 'memgraph' in self.config and NEO4J_AVAILABLE:
            try:
                self.executors['memgraph'] = MemgraphExecutor(self.config['memgraph'])
                logger.info("Memgraph executor initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Memgraph executor: {e}")

        # FalkorDB executor
        if 'falkordb' in self.config and REDIS_AVAILABLE:
            try:
                self.executors['falkordb'] = FalkorDBExecutor(self.config['falkordb'])
                logger.info("FalkorDB executor initialized")
            except Exception as e:
                logger.error(f"Failed to initialize FalkorDB executor: {e}")

        if not self.executors:
            raise RuntimeError("No database executors could be initialized")

    async def execute_cypher(self, cypher_query: CypherQuery,
                           database_type: str) -> CypherResult:
        """Execute Cypher query on specified database.

        Args:
            cypher_query: Cypher query to execute
            database_type: Target database type

        Returns:
            Query results
        """
        if database_type not in self.executors:
            raise ValueError(f"Database type {database_type} not available. "
                           f"Available: {list(self.executors.keys())}")

        executor = self.executors[database_type]

        # Ensure connection
        if not executor.is_connected():
            await executor.connect()

        # Execute query
        return await executor.execute(cypher_query)

    async def execute_on_all(self, cypher_query: CypherQuery) -> Dict[str, CypherResult]:
        """Execute query on all available databases.

        Args:
            cypher_query: Cypher query to execute

        Returns:
            Results from all databases
        """
        results = {}
        tasks = []

        for db_type, executor in self.executors.items():
            task = asyncio.create_task(
                self.execute_cypher(cypher_query, db_type),
                name=f"cypher_query_{db_type}"
            )
            tasks.append((db_type, task))

        # Wait for all tasks to complete
        for db_type, task in tasks:
            try:
                results[db_type] = await task
            except Exception as e:
                logger.error(f"Query failed on {db_type}: {e}")
                results[db_type] = CypherResult(
                    records=[],
                    summary={'error': str(e)},
                    execution_time=0.0,
                    database_type=db_type
                )

        return results

    def get_available_databases(self) -> List[str]:
        """Get list of available database types.

        Returns:
            List of available database type names
        """
        return list(self.executors.keys())

    async def close_all(self):
        """Close all database connections."""
        for executor in self.executors.values():
            await executor.close()
        logger.info("All Cypher executor connections closed")