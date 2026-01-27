"""
Shared fixtures for knowledge graph unit tests
"""

import pytest
from unittest.mock import Mock, AsyncMock

# Mock schema classes for testing
# Term type constants
IRI = "i"
LITERAL = "l"
BLANK = "b"
TRIPLE = "t"

class Term:
    def __init__(self, type, iri=None, value=None, id=None, datatype=None, language=None, triple=None):
        self.type = type
        self.iri = iri
        self.value = value
        self.id = id
        self.datatype = datatype
        self.language = language
        self.triple = triple

class Triple:
    def __init__(self, s, p, o):
        self.s = s
        self.p = p
        self.o = o

class Metadata:
    def __init__(self, id, user, collection, metadata):
        self.id = id
        self.user = user
        self.collection = collection
        self.metadata = metadata

class Triples:
    def __init__(self, metadata, triples):
        self.metadata = metadata
        self.triples = triples

class Chunk:
    def __init__(self, metadata, chunk):
        self.metadata = metadata
        self.chunk = chunk


@pytest.fixture
def sample_text():
    """Sample text for entity extraction testing"""
    return "John Smith works for OpenAI in San Francisco. He is a software engineer who developed GPT models."


@pytest.fixture
def sample_entities():
    """Sample extracted entities for testing"""
    return [
        {"text": "John Smith", "type": "PERSON", "start": 0, "end": 10},
        {"text": "OpenAI", "type": "ORG", "start": 21, "end": 27},
        {"text": "San Francisco", "type": "GPE", "start": 31, "end": 44},
        {"text": "software engineer", "type": "TITLE", "start": 55, "end": 72},
        {"text": "GPT models", "type": "PRODUCT", "start": 87, "end": 97}
    ]


@pytest.fixture
def sample_relationships():
    """Sample extracted relationships for testing"""
    return [
        {"subject": "John Smith", "predicate": "works_for", "object": "OpenAI"},
        {"subject": "OpenAI", "predicate": "located_in", "object": "San Francisco"},
        {"subject": "John Smith", "predicate": "has_title", "object": "software engineer"},
        {"subject": "John Smith", "predicate": "developed", "object": "GPT models"}
    ]


@pytest.fixture
def sample_term_uri():
    """Sample URI Term object"""
    return Term(
        type=IRI,
        iri="http://example.com/person/john-smith"
    )


@pytest.fixture
def sample_term_literal():
    """Sample literal Term object"""
    return Term(
        type=LITERAL,
        value="John Smith"
    )


@pytest.fixture
def sample_triple(sample_term_uri, sample_term_literal):
    """Sample Triple object"""
    return Triple(
        s=sample_term_uri,
        p=Term(type=IRI, iri="http://schema.org/name"),
        o=sample_term_literal
    )


@pytest.fixture
def sample_triples(sample_triple):
    """Sample Triples batch object"""
    metadata = Metadata(
        id="test-doc-123",
        user="test_user",
        collection="test_collection",
        metadata=[]
    )
    
    return Triples(
        metadata=metadata,
        triples=[sample_triple]
    )


@pytest.fixture
def sample_chunk():
    """Sample text chunk for processing"""
    metadata = Metadata(
        id="test-chunk-456",
        user="test_user",
        collection="test_collection",
        metadata=[]
    )
    
    return Chunk(
        metadata=metadata,
        chunk=b"Sample text chunk for knowledge graph extraction."
    )


@pytest.fixture
def mock_nlp_model():
    """Mock NLP model for entity recognition"""
    mock = Mock()
    mock.process_text.return_value = [
        {"text": "John Smith", "label": "PERSON", "start": 0, "end": 10},
        {"text": "OpenAI", "label": "ORG", "start": 21, "end": 27}
    ]
    return mock


@pytest.fixture
def mock_entity_extractor():
    """Mock entity extractor"""
    def extract_entities(text):
        if "John Smith" in text:
            return [
                {"text": "John Smith", "type": "PERSON", "confidence": 0.95},
                {"text": "OpenAI", "type": "ORG", "confidence": 0.92}
            ]
        return []
    
    return extract_entities


@pytest.fixture
def mock_relationship_extractor():
    """Mock relationship extractor"""
    def extract_relationships(entities, text):
        return [
            {"subject": "John Smith", "predicate": "works_for", "object": "OpenAI", "confidence": 0.88}
        ]
    
    return extract_relationships


@pytest.fixture
def uri_base():
    """Base URI for testing"""
    return "http://trustgraph.ai/kg"


@pytest.fixture
def namespace_mappings():
    """Namespace mappings for URI generation"""
    return {
        "person": "http://trustgraph.ai/kg/person/",
        "org": "http://trustgraph.ai/kg/org/",
        "place": "http://trustgraph.ai/kg/place/",
        "schema": "http://schema.org/",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    }


@pytest.fixture
def entity_type_mappings():
    """Entity type to namespace mappings"""
    return {
        "PERSON": "person",
        "ORG": "org",
        "GPE": "place",
        "LOCATION": "place"
    }


@pytest.fixture
def predicate_mappings():
    """Predicate mappings for relationships"""
    return {
        "works_for": "http://schema.org/worksFor",
        "located_in": "http://schema.org/location",
        "has_title": "http://schema.org/jobTitle",
        "developed": "http://schema.org/creator"
    }