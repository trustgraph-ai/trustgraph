from .registry import TranslatorRegistry
from .translators import *

# Auto-register all translators
from .translators.agent import AgentRequestTranslator, AgentResponseTranslator
from .translators.embeddings import EmbeddingsRequestTranslator, EmbeddingsResponseTranslator
from .translators.text_completion import TextCompletionRequestTranslator, TextCompletionResponseTranslator
from .translators.retrieval import (
    DocumentRagRequestTranslator, DocumentRagResponseTranslator,
    GraphRagRequestTranslator, GraphRagResponseTranslator
)
from .translators.triples import TriplesQueryRequestTranslator, TriplesQueryResponseTranslator
from .translators.knowledge import KnowledgeRequestTranslator, KnowledgeResponseTranslator
from .translators.library import LibraryRequestTranslator, LibraryResponseTranslator
from .translators.document_loading import DocumentTranslator, TextDocumentTranslator
from .translators.config import ConfigRequestTranslator, ConfigResponseTranslator
from .translators.flow import FlowRequestTranslator, FlowResponseTranslator
from .translators.prompt import PromptRequestTranslator, PromptResponseTranslator
from .translators.tool import ToolRequestTranslator, ToolResponseTranslator
from .translators.embeddings_query import (
    DocumentEmbeddingsRequestTranslator, DocumentEmbeddingsResponseTranslator,
    GraphEmbeddingsRequestTranslator, GraphEmbeddingsResponseTranslator
)
from .translators.objects_query import ObjectsQueryRequestTranslator, ObjectsQueryResponseTranslator
from .translators.nlp_query import QuestionToStructuredQueryRequestTranslator, QuestionToStructuredQueryResponseTranslator
from .translators.structured_query import StructuredQueryRequestTranslator, StructuredQueryResponseTranslator
from .translators.diagnosis import StructuredDataDiagnosisRequestTranslator, StructuredDataDiagnosisResponseTranslator

# Register all service translators
TranslatorRegistry.register_service(
    "agent", 
    AgentRequestTranslator(), 
    AgentResponseTranslator()
)

TranslatorRegistry.register_service(
    "embeddings", 
    EmbeddingsRequestTranslator(), 
    EmbeddingsResponseTranslator()
)

TranslatorRegistry.register_service(
    "text-completion", 
    TextCompletionRequestTranslator(), 
    TextCompletionResponseTranslator()
)

TranslatorRegistry.register_service(
    "document-rag", 
    DocumentRagRequestTranslator(), 
    DocumentRagResponseTranslator()
)

TranslatorRegistry.register_service(
    "graph-rag", 
    GraphRagRequestTranslator(), 
    GraphRagResponseTranslator()
)

TranslatorRegistry.register_service(
    "triples-query", 
    TriplesQueryRequestTranslator(), 
    TriplesQueryResponseTranslator()
)

TranslatorRegistry.register_service(
    "knowledge", 
    KnowledgeRequestTranslator(), 
    KnowledgeResponseTranslator()
)

TranslatorRegistry.register_service(
    "librarian", 
    LibraryRequestTranslator(), 
    LibraryResponseTranslator()
)

TranslatorRegistry.register_service(
    "config", 
    ConfigRequestTranslator(), 
    ConfigResponseTranslator()
)

TranslatorRegistry.register_service(
    "flow", 
    FlowRequestTranslator(), 
    FlowResponseTranslator()
)

TranslatorRegistry.register_service(
    "prompt", 
    PromptRequestTranslator(), 
    PromptResponseTranslator()
)

TranslatorRegistry.register_service(
    "tool", 
    ToolRequestTranslator(), 
    ToolResponseTranslator()
)

TranslatorRegistry.register_service(
    "document-embeddings-query", 
    DocumentEmbeddingsRequestTranslator(), 
    DocumentEmbeddingsResponseTranslator()
)

TranslatorRegistry.register_service(
    "graph-embeddings-query", 
    GraphEmbeddingsRequestTranslator(), 
    GraphEmbeddingsResponseTranslator()
)

TranslatorRegistry.register_service(
    "objects-query", 
    ObjectsQueryRequestTranslator(), 
    ObjectsQueryResponseTranslator()
)

TranslatorRegistry.register_service(
    "nlp-query", 
    QuestionToStructuredQueryRequestTranslator(), 
    QuestionToStructuredQueryResponseTranslator()
)

TranslatorRegistry.register_service(
    "structured-query",
    StructuredQueryRequestTranslator(),
    StructuredQueryResponseTranslator()
)

TranslatorRegistry.register_service(
    "structured-diag",
    StructuredDataDiagnosisRequestTranslator(),
    StructuredDataDiagnosisResponseTranslator()
)

# Register single-direction translators for document loading
TranslatorRegistry.register_request("document", DocumentTranslator())
TranslatorRegistry.register_request("text-document", TextDocumentTranslator())
