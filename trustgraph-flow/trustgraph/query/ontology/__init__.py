"""
OntoRAG Query System.

Ontology-driven natural language query processing with multi-backend support.
Provides semantic query understanding, ontology matching, and answer generation.
"""

from .query_service import OntoRAGQueryService, QueryRequest, QueryResponse
from .question_analyzer import QuestionAnalyzer, QuestionComponents, QuestionType
from .ontology_matcher import OntologyMatcher, QueryOntologySubset
from .backend_router import BackendRouter, BackendType, QueryRoute
from .sparql_generator import SPARQLGenerator, SPARQLQuery
from .sparql_cassandra import SPARQLCassandraEngine, SPARQLResult
from .cypher_generator import CypherGenerator, CypherQuery
from .cypher_executor import CypherExecutor, CypherResult
from .answer_generator import AnswerGenerator, GeneratedAnswer, AnswerMetadata

__all__ = [
    # Main service
    'OntoRAGQueryService',
    'QueryRequest',
    'QueryResponse',

    # Question analysis
    'QuestionAnalyzer',
    'QuestionComponents',
    'QuestionType',

    # Ontology matching
    'OntologyMatcher',
    'QueryOntologySubset',

    # Backend routing
    'BackendRouter',
    'BackendType',
    'QueryRoute',

    # SPARQL components
    'SPARQLGenerator',
    'SPARQLQuery',
    'SPARQLCassandraEngine',
    'SPARQLResult',

    # Cypher components
    'CypherGenerator',
    'CypherQuery',
    'CypherExecutor',
    'CypherResult',

    # Answer generation
    'AnswerGenerator',
    'GeneratedAnswer',
    'AnswerMetadata',
]