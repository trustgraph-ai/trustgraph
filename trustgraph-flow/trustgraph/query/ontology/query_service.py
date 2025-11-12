"""
Main OntoRAG query service.
Orchestrates question analysis, ontology matching, query generation, execution, and answer generation.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

from ....flow.flow_processor import FlowProcessor
from ....tables.config import ConfigTableStore
from ...extract.kg.ontology.ontology_loader import OntologyLoader
from ...extract.kg.ontology.vector_store import InMemoryVectorStore

from .question_analyzer import QuestionAnalyzer, QuestionComponents
from .ontology_matcher import OntologyMatcher, QueryOntologySubset
from .backend_router import BackendRouter, QueryRoute, BackendType
from .sparql_generator import SPARQLGenerator, SPARQLQuery
from .sparql_cassandra import SPARQLCassandraEngine, SPARQLResult
from .cypher_generator import CypherGenerator, CypherQuery
from .cypher_executor import CypherExecutor, CypherResult
from .answer_generator import AnswerGenerator, GeneratedAnswer

logger = logging.getLogger(__name__)


@dataclass
class QueryRequest:
    """Query request from user."""
    question: str
    context: Optional[str] = None
    ontology_hint: Optional[str] = None
    max_results: int = 10
    confidence_threshold: float = 0.7


@dataclass
class QueryResponse:
    """Complete query response."""
    answer: str
    confidence: float
    execution_time: float
    question_analysis: QuestionComponents
    ontology_subsets: List[QueryOntologySubset]
    query_route: QueryRoute
    generated_query: Union[SPARQLQuery, CypherQuery]
    raw_results: Union[SPARQLResult, CypherResult]
    supporting_facts: List[str]
    metadata: Dict[str, Any]


class OntoRAGQueryService(FlowProcessor):
    """Main OntoRAG query service orchestrating all components."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize OntoRAG query service.

        Args:
            config: Service configuration
        """
        super().__init__(config)
        self.config = config

        # Initialize components
        self.config_store = None
        self.ontology_loader = None
        self.vector_store = None
        self.question_analyzer = None
        self.ontology_matcher = None
        self.backend_router = None
        self.sparql_generator = None
        self.sparql_engine = None
        self.cypher_generator = None
        self.cypher_executor = None
        self.answer_generator = None

        # Cache for loaded ontologies
        self.ontology_cache = {}

    async def init(self):
        """Initialize all components."""
        await super().init()

        # Initialize configuration store
        self.config_store = ConfigTableStore(self.config.get('config_store', {}))

        # Initialize ontology components
        self.ontology_loader = OntologyLoader(self.config_store)

        # Initialize vector store
        vector_config = self.config.get('vector_store', {})
        self.vector_store = InMemoryVectorStore.create(
            store_type=vector_config.get('type', 'numpy'),
            dimension=vector_config.get('dimension', 384),
            similarity_threshold=vector_config.get('similarity_threshold', 0.7)
        )

        # Initialize question analyzer
        analyzer_config = self.config.get('question_analyzer', {})
        self.question_analyzer = QuestionAnalyzer(
            prompt_service=self.prompt_service,
            config=analyzer_config
        )

        # Initialize ontology matcher
        matcher_config = self.config.get('ontology_matcher', {})
        self.ontology_matcher = OntologyMatcher(
            vector_store=self.vector_store,
            embedding_service=self.embedding_service,
            config=matcher_config
        )

        # Initialize backend router
        router_config = self.config.get('backend_router', {})
        self.backend_router = BackendRouter(router_config)

        # Initialize query generators
        self.sparql_generator = SPARQLGenerator(prompt_service=self.prompt_service)
        self.cypher_generator = CypherGenerator(prompt_service=self.prompt_service)

        # Initialize executors
        sparql_config = self.config.get('sparql_executor', {})
        if self.backend_router.is_backend_enabled(BackendType.CASSANDRA):
            cassandra_config = self.backend_router.get_backend_config(BackendType.CASSANDRA)
            if cassandra_config:
                self.sparql_engine = SPARQLCassandraEngine(cassandra_config)
                await self.sparql_engine.initialize()

        cypher_config = self.config.get('cypher_executor', {})
        enabled_graph_backends = [
            bt for bt in [BackendType.NEO4J, BackendType.MEMGRAPH, BackendType.FALKORDB]
            if self.backend_router.is_backend_enabled(bt)
        ]
        if enabled_graph_backends:
            self.cypher_executor = CypherExecutor(cypher_config)
            await self.cypher_executor.initialize()

        # Initialize answer generator
        self.answer_generator = AnswerGenerator(prompt_service=self.prompt_service)

        logger.info("OntoRAG query service initialized")

    async def process(self, request: QueryRequest) -> QueryResponse:
        """Process a natural language query.

        Args:
            request: Query request

        Returns:
            Complete query response
        """
        start_time = datetime.now()

        try:
            logger.info(f"Processing query: {request.question}")

            # Step 1: Analyze question
            question_components = await self.question_analyzer.analyze_question(
                request.question, context=request.context
            )
            logger.debug(f"Question analysis: {question_components.question_type}")

            # Step 2: Load and match ontologies
            ontology_subsets = await self._load_and_match_ontologies(
                question_components, request.ontology_hint
            )
            logger.debug(f"Found {len(ontology_subsets)} relevant ontology subsets")

            # Step 3: Route to appropriate backend
            query_route = self.backend_router.route_query(
                question_components, ontology_subsets
            )
            logger.debug(f"Routed to {query_route.backend_type.value} backend")

            # Step 4: Generate and execute query
            if query_route.query_language == 'sparql':
                query_results = await self._execute_sparql_path(
                    question_components, ontology_subsets, query_route
                )
            else:  # cypher
                query_results = await self._execute_cypher_path(
                    question_components, ontology_subsets, query_route
                )

            # Step 5: Generate natural language answer
            generated_answer = await self.answer_generator.generate_answer(
                question_components,
                query_results['raw_results'],
                ontology_subsets[0] if ontology_subsets else None,
                query_route.backend_type.value
            )

            # Build response
            execution_time = (datetime.now() - start_time).total_seconds()

            response = QueryResponse(
                answer=generated_answer.answer,
                confidence=min(query_route.confidence, generated_answer.metadata.confidence),
                execution_time=execution_time,
                question_analysis=question_components,
                ontology_subsets=ontology_subsets,
                query_route=query_route,
                generated_query=query_results['generated_query'],
                raw_results=query_results['raw_results'],
                supporting_facts=generated_answer.supporting_facts,
                metadata={
                    'backend_used': query_route.backend_type.value,
                    'query_language': query_route.query_language,
                    'ontology_count': len(ontology_subsets),
                    'result_count': generated_answer.metadata.result_count,
                    'routing_reasoning': query_route.reasoning,
                    'generation_time': generated_answer.generation_time
                }
            )

            logger.info(f"Query processed successfully in {execution_time:.2f}s")
            return response

        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            execution_time = (datetime.now() - start_time).total_seconds()

            # Return error response
            return QueryResponse(
                answer=f"I encountered an error processing your query: {str(e)}",
                confidence=0.0,
                execution_time=execution_time,
                question_analysis=QuestionComponents(
                    original_question=request.question,
                    normalized_question=request.question,
                    question_type=None,
                    entities=[], keywords=[], relationships=[], constraints=[],
                    aggregations=[], expected_answer_type="unknown"
                ),
                ontology_subsets=[],
                query_route=None,
                generated_query=None,
                raw_results=None,
                supporting_facts=[],
                metadata={'error': str(e), 'execution_time': execution_time}
            )

    async def _load_and_match_ontologies(self,
                                       question_components: QuestionComponents,
                                       ontology_hint: Optional[str] = None) -> List[QueryOntologySubset]:
        """Load ontologies and find relevant subsets.

        Args:
            question_components: Analyzed question
            ontology_hint: Optional ontology hint

        Returns:
            List of relevant ontology subsets
        """
        try:
            # Load available ontologies
            if ontology_hint:
                # Load specific ontology
                ontologies = [await self.ontology_loader.load_ontology(ontology_hint)]
            else:
                # Load all available ontologies
                available_ontologies = await self.ontology_loader.list_available_ontologies()
                ontologies = []
                for ontology_id in available_ontologies[:5]:  # Limit to 5 for performance
                    try:
                        ontology = await self.ontology_loader.load_ontology(ontology_id)
                        ontologies.append(ontology)
                    except Exception as e:
                        logger.warning(f"Failed to load ontology {ontology_id}: {e}")

            if not ontologies:
                logger.warning("No ontologies loaded")
                return []

            # Extract relevant subsets
            ontology_subsets = []
            for ontology in ontologies:
                subset = await self.ontology_matcher.select_relevant_subset(
                    question_components, ontology
                )
                if subset and (subset.classes or subset.object_properties or subset.datatype_properties):
                    ontology_subsets.append(subset)

            return ontology_subsets

        except Exception as e:
            logger.error(f"Failed to load and match ontologies: {e}")
            return []

    async def _execute_sparql_path(self,
                                 question_components: QuestionComponents,
                                 ontology_subsets: List[QueryOntologySubset],
                                 query_route: QueryRoute) -> Dict[str, Any]:
        """Execute SPARQL query path.

        Args:
            question_components: Question analysis
            ontology_subsets: Ontology subsets
            query_route: Query route

        Returns:
            Query execution results
        """
        if not self.sparql_engine:
            raise RuntimeError("SPARQL engine not initialized")

        # Generate SPARQL query
        primary_subset = ontology_subsets[0] if ontology_subsets else None
        sparql_query = await self.sparql_generator.generate_sparql(
            question_components, primary_subset
        )

        logger.debug(f"Generated SPARQL: {sparql_query.query}")

        # Execute query
        sparql_results = self.sparql_engine.execute_sparql(sparql_query.query)

        return {
            'generated_query': sparql_query,
            'raw_results': sparql_results
        }

    async def _execute_cypher_path(self,
                                 question_components: QuestionComponents,
                                 ontology_subsets: List[QueryOntologySubset],
                                 query_route: QueryRoute) -> Dict[str, Any]:
        """Execute Cypher query path.

        Args:
            question_components: Question analysis
            ontology_subsets: Ontology subsets
            query_route: Query route

        Returns:
            Query execution results
        """
        if not self.cypher_executor:
            raise RuntimeError("Cypher executor not initialized")

        # Generate Cypher query
        primary_subset = ontology_subsets[0] if ontology_subsets else None
        cypher_query = await self.cypher_generator.generate_cypher(
            question_components, primary_subset
        )

        logger.debug(f"Generated Cypher: {cypher_query.query}")

        # Execute query
        database_type = query_route.backend_type.value
        cypher_results = await self.cypher_executor.execute_query(
            cypher_query.query, database_type=database_type
        )

        return {
            'generated_query': cypher_query,
            'raw_results': cypher_results
        }

    async def get_supported_backends(self) -> List[str]:
        """Get list of supported and enabled backends.

        Returns:
            List of backend names
        """
        return [bt.value for bt in self.backend_router.get_available_backends()]

    async def get_available_ontologies(self) -> List[str]:
        """Get list of available ontologies.

        Returns:
            List of ontology identifiers
        """
        if self.ontology_loader:
            return await self.ontology_loader.list_available_ontologies()
        return []

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all components.

        Returns:
            Health status of all components
        """
        health = {
            'service': 'healthy',
            'components': {},
            'backends': {},
            'ontologies': {}
        }

        try:
            # Check ontology loader
            if self.ontology_loader:
                ontologies = await self.ontology_loader.list_available_ontologies()
                health['components']['ontology_loader'] = 'healthy'
                health['ontologies']['count'] = len(ontologies)
            else:
                health['components']['ontology_loader'] = 'not_initialized'

            # Check vector store
            if self.vector_store:
                health['components']['vector_store'] = 'healthy'
                health['components']['vector_store_type'] = type(self.vector_store).__name__
            else:
                health['components']['vector_store'] = 'not_initialized'

            # Check backends
            for backend_type in self.backend_router.get_available_backends():
                if backend_type == BackendType.CASSANDRA and self.sparql_engine:
                    health['backends']['cassandra'] = 'healthy'
                elif backend_type in [BackendType.NEO4J, BackendType.MEMGRAPH, BackendType.FALKORDB] and self.cypher_executor:
                    health['backends'][backend_type.value] = 'healthy'
                else:
                    health['backends'][backend_type.value] = 'configured_but_not_initialized'

        except Exception as e:
            health['service'] = 'degraded'
            health['error'] = str(e)

        return health

    async def close(self):
        """Close all connections and cleanup resources."""
        try:
            if self.sparql_engine:
                self.sparql_engine.close()

            if self.cypher_executor:
                await self.cypher_executor.close()

            if self.config_store:
                # ConfigTableStore cleanup if needed
                pass

            logger.info("OntoRAG query service closed")

        except Exception as e:
            logger.error(f"Error closing OntoRAG query service: {e}")