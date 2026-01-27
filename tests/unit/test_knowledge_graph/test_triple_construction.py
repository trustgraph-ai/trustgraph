"""
Unit tests for triple construction logic

Tests the core business logic for constructing RDF triples from extracted
entities and relationships, including URI generation, Term object creation,
and triple validation.
"""

import pytest
from unittest.mock import Mock
from .conftest import Triple, Triples, Term, Metadata, IRI, LITERAL
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

    def test_term_object_creation(self):
        """Test creation of Term objects for subjects, predicates, and objects"""
        # Arrange
        def create_term_object(text, is_uri, datatype=""):
            if is_uri:
                return Term(type=IRI, iri=text)
            else:
                return Term(type=LITERAL, value=text, datatype=datatype if datatype else None)

        test_cases = [
            ("http://trustgraph.ai/kg/person/john-smith", True, ""),
            ("John Smith", False, "string"),
            ("42", False, "integer"),
            ("http://schema.org/worksFor", True, "")
        ]

        # Act & Assert
        for value_text, is_uri, datatype in test_cases:
            term_obj = create_term_object(value_text, is_uri, datatype)

            assert isinstance(term_obj, Term)
            if is_uri:
                assert term_obj.type == IRI
                assert term_obj.iri == value_text
            else:
                assert term_obj.type == LITERAL
                assert term_obj.value == value_text

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

            # Create Term objects
            subject_term = Term(type=IRI, iri=subject_uri)
            predicate_term = Term(type=IRI, iri=predicate_uri)
            object_term = Term(type=IRI, iri=object_uri)

            # Create Triple
            return Triple(
                s=subject_term,
                p=predicate_term,
                o=object_term
            )

        # Act
        triple = construct_triple(relationship)

        # Assert
        assert isinstance(triple, Triple)
        assert triple.s.iri == "http://trustgraph.ai/kg/person/john-smith"
        assert triple.s.type == IRI
        assert triple.p.iri == "http://schema.org/worksFor"
        assert triple.p.type == IRI
        assert triple.o.iri == "http://trustgraph.ai/kg/org/openai"
        assert triple.o.type == IRI

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
            subject_term = Term(type=IRI, iri=subject_uri)

            # Determine predicate URI
            predicate_mappings = {
                "name": "http://schema.org/name",
                "age": "http://schema.org/age",
                "email": "http://schema.org/email",
                "worksFor": "http://schema.org/worksFor"
            }
            predicate_uri = predicate_mappings.get(predicate, f"http://trustgraph.ai/kg/predicate/{predicate}")
            predicate_term = Term(type=IRI, iri=predicate_uri)

            # Create object term with appropriate type
            if object_is_uri:
                object_term = Term(type=IRI, iri=object_value)
            else:
                datatype = None
                if predicate == "age":
                    datatype = "integer"
                elif predicate in ["name", "email"]:
                    datatype = "string"
                object_term = Term(type=LITERAL, value=object_value, datatype=datatype)

            return Triple(s=subject_term, p=predicate_term, o=object_term)

        # Act & Assert
        for subject_uri, predicate, object_value, object_is_uri in test_data:
            subject_full_uri = "http://trustgraph.ai/kg/person/john-smith"
            triple = create_triple_with_literal(subject_full_uri, predicate, object_value, object_is_uri)

            if object_is_uri:
                assert triple.o.type == IRI
                assert triple.o.iri == object_value
            else:
                assert triple.o.type == LITERAL
                assert triple.o.value == object_value

            if predicate == "age":
                assert triple.o.datatype == "integer"
            elif predicate in ["name", "email"]:
                assert triple.o.datatype == "string"

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
        def get_term_value(term):
            """Extract value from a Term"""
            if term.type == IRI:
                return term.iri
            else:
                return term.value

        def validate_triple(triple):
            errors = []

            # Check required components
            s_val = get_term_value(triple.s) if triple.s else None
            p_val = get_term_value(triple.p) if triple.p else None
            o_val = get_term_value(triple.o) if triple.o else None

            if not triple.s or not s_val:
                errors.append("Missing or empty subject")

            if not triple.p or not p_val:
                errors.append("Missing or empty predicate")

            if not triple.o or not o_val:
                errors.append("Missing or empty object")

            # Check URI validity for URI values
            uri_pattern = r'^https?://[^\s/$.?#].[^\s]*$'

            if triple.s.type == IRI and not re.match(uri_pattern, triple.s.iri or ""):
                errors.append("Invalid subject URI format")

            if triple.p.type == IRI and not re.match(uri_pattern, triple.p.iri or ""):
                errors.append("Invalid predicate URI format")

            if triple.o.type == IRI and not re.match(uri_pattern, triple.o.iri or ""):
                errors.append("Invalid object URI format")

            # Predicates should typically be URIs
            if triple.p.type != IRI:
                errors.append("Predicate should be a URI")

            return len(errors) == 0, errors

        # Test valid triple
        valid_triple = Triple(
            s=Term(type=IRI, iri="http://trustgraph.ai/kg/person/john"),
            p=Term(type=IRI, iri="http://schema.org/name"),
            o=Term(type=LITERAL, value="John Smith", datatype="string")
        )

        # Test invalid triples
        invalid_triples = [
            Triple(s=Term(type=IRI, iri=""),
                  p=Term(type=IRI, iri="http://schema.org/name"),
                  o=Term(type=LITERAL, value="John")),  # Empty subject

            Triple(s=Term(type=IRI, iri="http://trustgraph.ai/kg/person/john"),
                  p=Term(type=LITERAL, value="name"),  # Non-URI predicate
                  o=Term(type=LITERAL, value="John")),

            Triple(s=Term(type=IRI, iri="invalid-uri"),
                  p=Term(type=IRI, iri="http://schema.org/name"),
                  o=Term(type=LITERAL, value="John"))  # Invalid URI format
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
                    s=Term(type=IRI, iri=entity_uri),
                    p=Term(type=IRI, iri="http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                    o=Term(type=IRI, iri=type_uri)
                )
                triples.append(type_triple)

            # Create relationship triples
            for rel in relationships:
                subject_uri = f"http://trustgraph.ai/kg/entity/{rel['subject'].lower().replace(' ', '-')}"
                object_uri = f"http://trustgraph.ai/kg/entity/{rel['object'].lower().replace(' ', '-')}"
                predicate_uri = f"http://schema.org/{rel['predicate'].replace('_', '')}"

                rel_triple = Triple(
                    s=Term(type=IRI, iri=subject_uri),
                    p=Term(type=IRI, iri=predicate_uri),
                    o=Term(type=IRI, iri=object_uri)
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
            assert triple.s.iri != ""
            assert triple.p.iri != ""
            assert triple.o.iri != ""

    def test_triples_batch_object_creation(self):
        """Test creating Triples batch objects with metadata"""
        # Arrange
        sample_triples = [
            Triple(
                s=Term(type=IRI, iri="http://trustgraph.ai/kg/person/john"),
                p=Term(type=IRI, iri="http://schema.org/name"),
                o=Term(type=LITERAL, value="John Smith", datatype="string")
            ),
            Triple(
                s=Term(type=IRI, iri="http://trustgraph.ai/kg/person/john"),
                p=Term(type=IRI, iri="http://schema.org/worksFor"),
                o=Term(type=IRI, iri="http://trustgraph.ai/kg/org/openai")
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
            assert isinstance(triple.s, Term)
            assert isinstance(triple.p, Term)
            assert isinstance(triple.o, Term)

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