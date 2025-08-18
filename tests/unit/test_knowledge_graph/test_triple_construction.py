"""
Unit tests for triple construction logic

Tests the core business logic for constructing RDF triples from extracted
entities and relationships, including URI generation, Value object creation,
and triple validation.
"""

import pytest
from unittest.mock import Mock
from .conftest import Triple, Triples, Value, Metadata
import re
import hashlib


class TestTripleConstructionLogic:
    """Test cases for triple construction business logic"""

    def test_uri_generation_from_text(self):
        """Test URI generation from entity text"""
        # Arrange
        def generate_uri(text, entity_type, base_uri="http://trustgraph.ai/kg"):
            # Normalize text for URI
            normalized = text.lower()
            normalized = re.sub(r'[^\w\s-]', '', normalized)  # Remove special chars
            normalized = re.sub(r'\s+', '-', normalized.strip())  # Replace spaces with hyphens
            
            # Map entity types to namespaces
            type_mappings = {
                "PERSON": "person",
                "ORG": "org", 
                "PLACE": "place",
                "PRODUCT": "product"
            }
            
            namespace = type_mappings.get(entity_type, "entity")
            return f"{base_uri}/{namespace}/{normalized}"
        
        test_cases = [
            ("John Smith", "PERSON", "http://trustgraph.ai/kg/person/john-smith"),
            ("OpenAI Inc.", "ORG", "http://trustgraph.ai/kg/org/openai-inc"),
            ("San Francisco", "PLACE", "http://trustgraph.ai/kg/place/san-francisco"),
            ("GPT-4", "PRODUCT", "http://trustgraph.ai/kg/product/gpt-4")
        ]
        
        # Act & Assert
        for text, entity_type, expected_uri in test_cases:
            generated_uri = generate_uri(text, entity_type)
            assert generated_uri == expected_uri, f"URI generation failed for '{text}'"

    def test_value_object_creation(self):
        """Test creation of Value objects for subjects, predicates, and objects"""
        # Arrange
        def create_value_object(text, is_uri, value_type=""):
            return Value(
                value=text,
                is_uri=is_uri,
                type=value_type
            )
        
        test_cases = [
            ("http://trustgraph.ai/kg/person/john-smith", True, ""),
            ("John Smith", False, "string"),
            ("42", False, "integer"),
            ("http://schema.org/worksFor", True, "")
        ]
        
        # Act & Assert
        for value_text, is_uri, value_type in test_cases:
            value_obj = create_value_object(value_text, is_uri, value_type)
            
            assert isinstance(value_obj, Value)
            assert value_obj.value == value_text
            assert value_obj.is_uri == is_uri
            assert value_obj.type == value_type

    def test_triple_construction_from_relationship(self):
        """Test constructing Triple objects from relationships"""
        # Arrange
        relationship = {
            "subject": "John Smith",
            "predicate": "works_for", 
            "object": "OpenAI",
            "subject_type": "PERSON",
            "object_type": "ORG"
        }
        
        def construct_triple(relationship, uri_base="http://trustgraph.ai/kg"):
            # Generate URIs
            subject_uri = f"{uri_base}/person/{relationship['subject'].lower().replace(' ', '-')}"
            object_uri = f"{uri_base}/org/{relationship['object'].lower().replace(' ', '-')}"
            
            # Map predicate to schema.org URI
            predicate_mappings = {
                "works_for": "http://schema.org/worksFor",
                "located_in": "http://schema.org/location",
                "developed": "http://schema.org/creator"
            }
            predicate_uri = predicate_mappings.get(relationship["predicate"], 
                                                 f"{uri_base}/predicate/{relationship['predicate']}")
            
            # Create Value objects
            subject_value = Value(value=subject_uri, is_uri=True, type="")
            predicate_value = Value(value=predicate_uri, is_uri=True, type="")
            object_value = Value(value=object_uri, is_uri=True, type="")
            
            # Create Triple
            return Triple(
                s=subject_value,
                p=predicate_value,
                o=object_value
            )
        
        # Act
        triple = construct_triple(relationship)
        
        # Assert
        assert isinstance(triple, Triple)
        assert triple.s.value == "http://trustgraph.ai/kg/person/john-smith"
        assert triple.s.is_uri is True
        assert triple.p.value == "http://schema.org/worksFor"
        assert triple.p.is_uri is True
        assert triple.o.value == "http://trustgraph.ai/kg/org/openai"
        assert triple.o.is_uri is True

    def test_literal_value_handling(self):
        """Test handling of literal values vs URI values"""
        # Arrange
        test_data = [
            ("John Smith", "name", "John Smith", False),  # Literal name
            ("John Smith", "age", "30", False),  # Literal age
            ("John Smith", "email", "john@example.com", False),  # Literal email
            ("John Smith", "worksFor", "http://trustgraph.ai/kg/org/openai", True)  # URI reference
        ]
        
        def create_triple_with_literal(subject_uri, predicate, object_value, object_is_uri):
            subject_val = Value(value=subject_uri, is_uri=True, type="")
            
            # Determine predicate URI
            predicate_mappings = {
                "name": "http://schema.org/name",
                "age": "http://schema.org/age",
                "email": "http://schema.org/email",
                "worksFor": "http://schema.org/worksFor"
            }
            predicate_uri = predicate_mappings.get(predicate, f"http://trustgraph.ai/kg/predicate/{predicate}")
            predicate_val = Value(value=predicate_uri, is_uri=True, type="")
            
            # Create object value with appropriate type
            object_type = ""
            if not object_is_uri:
                if predicate == "age":
                    object_type = "integer"
                elif predicate in ["name", "email"]:
                    object_type = "string"
            
            object_val = Value(value=object_value, is_uri=object_is_uri, type=object_type)
            
            return Triple(s=subject_val, p=predicate_val, o=object_val)
        
        # Act & Assert
        for subject_uri, predicate, object_value, object_is_uri in test_data:
            subject_full_uri = "http://trustgraph.ai/kg/person/john-smith"
            triple = create_triple_with_literal(subject_full_uri, predicate, object_value, object_is_uri)
            
            assert triple.o.is_uri == object_is_uri
            assert triple.o.value == object_value
            
            if predicate == "age":
                assert triple.o.type == "integer"
            elif predicate in ["name", "email"]:
                assert triple.o.type == "string"

    def test_namespace_management(self):
        """Test namespace prefix management and expansion"""
        # Arrange
        namespaces = {
            "tg": "http://trustgraph.ai/kg/",
            "schema": "http://schema.org/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
        }
        
        def expand_prefixed_uri(prefixed_uri, namespaces):
            if ":" not in prefixed_uri:
                return prefixed_uri
            
            prefix, local_name = prefixed_uri.split(":", 1)
            if prefix in namespaces:
                return namespaces[prefix] + local_name
            return prefixed_uri
        
        def create_prefixed_uri(full_uri, namespaces):
            for prefix, namespace_uri in namespaces.items():
                if full_uri.startswith(namespace_uri):
                    local_name = full_uri[len(namespace_uri):]
                    return f"{prefix}:{local_name}"
            return full_uri
        
        # Act & Assert
        test_cases = [
            ("tg:person/john-smith", "http://trustgraph.ai/kg/person/john-smith"),
            ("schema:worksFor", "http://schema.org/worksFor"),
            ("rdf:type", "http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
        ]
        
        for prefixed, expanded in test_cases:
            # Test expansion
            result = expand_prefixed_uri(prefixed, namespaces)
            assert result == expanded
            
            # Test compression
            compressed = create_prefixed_uri(expanded, namespaces)
            assert compressed == prefixed

    def test_triple_validation(self):
        """Test triple validation rules"""
        # Arrange
        def validate_triple(triple):
            errors = []
            
            # Check required components
            if not triple.s or not triple.s.value:
                errors.append("Missing or empty subject")
            
            if not triple.p or not triple.p.value:
                errors.append("Missing or empty predicate")
            
            if not triple.o or not triple.o.value:
                errors.append("Missing or empty object")
            
            # Check URI validity for URI values
            uri_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
            
            if triple.s.is_uri and not re.match(uri_pattern, triple.s.value):
                errors.append("Invalid subject URI format")
            
            if triple.p.is_uri and not re.match(uri_pattern, triple.p.value):
                errors.append("Invalid predicate URI format")
            
            if triple.o.is_uri and not re.match(uri_pattern, triple.o.value):
                errors.append("Invalid object URI format")
            
            # Predicates should typically be URIs
            if not triple.p.is_uri:
                errors.append("Predicate should be a URI")
            
            return len(errors) == 0, errors
        
        # Test valid triple
        valid_triple = Triple(
            s=Value(value="http://trustgraph.ai/kg/person/john", is_uri=True, type=""),
            p=Value(value="http://schema.org/name", is_uri=True, type=""),
            o=Value(value="John Smith", is_uri=False, type="string")
        )
        
        # Test invalid triples
        invalid_triples = [
            Triple(s=Value(value="", is_uri=True, type=""), 
                  p=Value(value="http://schema.org/name", is_uri=True, type=""),
                  o=Value(value="John", is_uri=False, type="")),  # Empty subject
            
            Triple(s=Value(value="http://trustgraph.ai/kg/person/john", is_uri=True, type=""), 
                  p=Value(value="name", is_uri=False, type=""),  # Non-URI predicate
                  o=Value(value="John", is_uri=False, type="")),
            
            Triple(s=Value(value="invalid-uri", is_uri=True, type=""), 
                  p=Value(value="http://schema.org/name", is_uri=True, type=""),
                  o=Value(value="John", is_uri=False, type=""))  # Invalid URI format
        ]
        
        # Act & Assert
        is_valid, errors = validate_triple(valid_triple)
        assert is_valid, f"Valid triple failed validation: {errors}"
        
        for invalid_triple in invalid_triples:
            is_valid, errors = validate_triple(invalid_triple)
            assert not is_valid, f"Invalid triple passed validation: {invalid_triple}"
            assert len(errors) > 0

    def test_batch_triple_construction(self):
        """Test constructing multiple triples from entity/relationship data"""
        # Arrange
        entities = [
            {"text": "John Smith", "type": "PERSON"},
            {"text": "OpenAI", "type": "ORG"},
            {"text": "San Francisco", "type": "PLACE"}
        ]
        
        relationships = [
            {"subject": "John Smith", "predicate": "works_for", "object": "OpenAI"},
            {"subject": "OpenAI", "predicate": "located_in", "object": "San Francisco"}
        ]
        
        def construct_triple_batch(entities, relationships, document_id="doc-1"):
            triples = []
            
            # Create type triples for entities
            for entity in entities:
                entity_uri = f"http://trustgraph.ai/kg/{entity['type'].lower()}/{entity['text'].lower().replace(' ', '-')}"
                type_uri = f"http://trustgraph.ai/kg/type/{entity['type']}"
                
                type_triple = Triple(
                    s=Value(value=entity_uri, is_uri=True, type=""),
                    p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True, type=""),
                    o=Value(value=type_uri, is_uri=True, type="")
                )
                triples.append(type_triple)
            
            # Create relationship triples
            for rel in relationships:
                subject_uri = f"http://trustgraph.ai/kg/entity/{rel['subject'].lower().replace(' ', '-')}"
                object_uri = f"http://trustgraph.ai/kg/entity/{rel['object'].lower().replace(' ', '-')}"
                predicate_uri = f"http://schema.org/{rel['predicate'].replace('_', '')}"
                
                rel_triple = Triple(
                    s=Value(value=subject_uri, is_uri=True, type=""),
                    p=Value(value=predicate_uri, is_uri=True, type=""),
                    o=Value(value=object_uri, is_uri=True, type="")
                )
                triples.append(rel_triple)
            
            return triples
        
        # Act
        triples = construct_triple_batch(entities, relationships)
        
        # Assert
        assert len(triples) == len(entities) + len(relationships)  # Type triples + relationship triples
        
        # Check that all triples are valid Triple objects
        for triple in triples:
            assert isinstance(triple, Triple)
            assert triple.s.value != ""
            assert triple.p.value != ""
            assert triple.o.value != ""

    def test_triples_batch_object_creation(self):
        """Test creating Triples batch objects with metadata"""
        # Arrange
        sample_triples = [
            Triple(
                s=Value(value="http://trustgraph.ai/kg/person/john", is_uri=True, type=""),
                p=Value(value="http://schema.org/name", is_uri=True, type=""),
                o=Value(value="John Smith", is_uri=False, type="string")
            ),
            Triple(
                s=Value(value="http://trustgraph.ai/kg/person/john", is_uri=True, type=""),
                p=Value(value="http://schema.org/worksFor", is_uri=True, type=""),
                o=Value(value="http://trustgraph.ai/kg/org/openai", is_uri=True, type="")
            )
        ]
        
        metadata = Metadata(
            id="test-doc-123",
            user="test_user", 
            collection="test_collection",
            metadata=[]
        )
        
        # Act
        triples_batch = Triples(
            metadata=metadata,
            triples=sample_triples
        )
        
        # Assert
        assert isinstance(triples_batch, Triples)
        assert triples_batch.metadata.id == "test-doc-123"
        assert triples_batch.metadata.user == "test_user"
        assert triples_batch.metadata.collection == "test_collection"
        assert len(triples_batch.triples) == 2
        
        # Check that triples are properly embedded
        for triple in triples_batch.triples:
            assert isinstance(triple, Triple)
            assert isinstance(triple.s, Value)
            assert isinstance(triple.p, Value)
            assert isinstance(triple.o, Value)

    def test_uri_collision_handling(self):
        """Test handling of URI collisions and duplicate detection"""
        # Arrange
        entities = [
            {"text": "John Smith", "type": "PERSON", "context": "Engineer at OpenAI"},
            {"text": "John Smith", "type": "PERSON", "context": "Professor at Stanford"},
            {"text": "Apple Inc.", "type": "ORG", "context": "Technology company"},
            {"text": "Apple", "type": "PRODUCT", "context": "Fruit"}
        ]
        
        def generate_unique_uri(entity, existing_uris):
            base_text = entity["text"].lower().replace(" ", "-")
            entity_type = entity["type"].lower()
            base_uri = f"http://trustgraph.ai/kg/{entity_type}/{base_text}"
            
            # If URI doesn't exist, use it
            if base_uri not in existing_uris:
                return base_uri
            
            # Generate hash from context to create unique identifier
            context = entity.get("context", "")
            context_hash = hashlib.md5(context.encode()).hexdigest()[:8]
            unique_uri = f"{base_uri}-{context_hash}"
            
            return unique_uri
        
        # Act
        generated_uris = []
        existing_uris = set()
        
        for entity in entities:
            uri = generate_unique_uri(entity, existing_uris)
            generated_uris.append(uri)
            existing_uris.add(uri)
        
        # Assert
        # All URIs should be unique
        assert len(generated_uris) == len(set(generated_uris))
        
        # Both John Smith entities should have different URIs
        john_smith_uris = [uri for uri in generated_uris if "john-smith" in uri]
        assert len(john_smith_uris) == 2
        assert john_smith_uris[0] != john_smith_uris[1]
        
        # Apple entities should have different URIs due to different types
        apple_uris = [uri for uri in generated_uris if "apple" in uri]
        assert len(apple_uris) == 2
        assert apple_uris[0] != apple_uris[1]