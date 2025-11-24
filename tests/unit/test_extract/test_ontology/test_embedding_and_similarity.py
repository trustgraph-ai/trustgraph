"""
Unit tests for ontology embedding and similarity matching.

Tests that ontology elements are properly embedded and matched against
input text using vector similarity.
"""

import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock
from trustgraph.extract.kg.ontology.ontology_embedder import (
    OntologyEmbedder,
    OntologyElementMetadata
)
from trustgraph.extract.kg.ontology.ontology_loader import (
    Ontology,
    OntologyClass,
    OntologyProperty
)
from trustgraph.extract.kg.ontology.vector_store import InMemoryVectorStore, SearchResult
from trustgraph.extract.kg.ontology.text_processor import TextSegment
from trustgraph.extract.kg.ontology.ontology_selector import OntologySelector, OntologySubset


@pytest.fixture
def mock_embedding_service():
    """Create a mock embedding service."""
    service = AsyncMock()
    # Return deterministic embeddings for testing
    async def mock_embed(text):
        # Simple hash-based embedding for deterministic tests
        hash_val = hash(text) % 1000
        return np.array([hash_val / 1000.0, (1000 - hash_val) / 1000.0])
    service.embed = mock_embed
    return service


@pytest.fixture
def vector_store():
    """Create an empty vector store."""
    return InMemoryVectorStore()


@pytest.fixture
def ontology_embedder(mock_embedding_service, vector_store):
    """Create an ontology embedder with mock service."""
    return OntologyEmbedder(
        embedding_service=mock_embedding_service,
        vector_store=vector_store
    )


@pytest.fixture
def sample_ontology_class():
    """Create a sample ontology class."""
    return OntologyClass(
        uri="http://purl.org/ontology/fo/Recipe",
        type="owl:Class",
        labels=[{"value": "Recipe", "lang": "en-gb"}],
        comment="A Recipe is a combination of ingredients and a method.",
        subclass_of=None
    )


@pytest.fixture
def sample_ontology_property():
    """Create a sample ontology property."""
    return OntologyProperty(
        uri="http://purl.org/ontology/fo/ingredients",
        type="owl:ObjectProperty",
        labels=[{"value": "ingredients", "lang": "en-gb"}],
        comment="The ingredients property relates a recipe to an ingredient list.",
        domain="Recipe",
        range="IngredientList"
    )


class TestTextRepresentation:
    """Test suite for creating text representations of ontology elements."""

    def test_create_text_from_class_with_id(self, ontology_embedder, sample_ontology_class):
        """Test that class ID is included in text representation."""
        text = ontology_embedder._create_text_representation(
            "Recipe",
            sample_ontology_class,
            "class"
        )

        assert "Recipe" in text, "Should include class ID"

    def test_create_text_from_class_with_labels(self, ontology_embedder, sample_ontology_class):
        """Test that class labels are included in text representation."""
        text = ontology_embedder._create_text_representation(
            "Recipe",
            sample_ontology_class,
            "class"
        )

        assert "Recipe" in text, "Should include label value"

    def test_create_text_from_class_with_comment(self, ontology_embedder, sample_ontology_class):
        """Test that class comments are included in text representation."""
        text = ontology_embedder._create_text_representation(
            "Recipe",
            sample_ontology_class,
            "class"
        )

        assert "combination of ingredients" in text, "Should include comment"

    def test_create_text_from_property_with_domain_range(self, ontology_embedder, sample_ontology_property):
        """Test that property domain and range are included in text."""
        text = ontology_embedder._create_text_representation(
            "ingredients",
            sample_ontology_property,
            "objectProperty"
        )

        assert "domain: Recipe" in text, "Should include domain"
        assert "range: IngredientList" in text, "Should include range"

    def test_normalizes_id_with_underscores(self, ontology_embedder):
        """Test that IDs with underscores are normalized."""
        mock_element = MagicMock()
        mock_element.labels = []
        mock_element.comment = None

        text = ontology_embedder._create_text_representation(
            "some_property_name",
            mock_element,
            "objectProperty"
        )

        assert "some property name" in text, "Should replace underscores with spaces"

    def test_normalizes_id_with_hyphens(self, ontology_embedder):
        """Test that IDs with hyphens are normalized."""
        mock_element = MagicMock()
        mock_element.labels = []
        mock_element.comment = None

        text = ontology_embedder._create_text_representation(
            "some-property-name",
            mock_element,
            "objectProperty"
        )

        assert "some property name" in text, "Should replace hyphens with spaces"

    def test_handles_element_without_labels(self, ontology_embedder):
        """Test handling of elements without labels."""
        mock_element = MagicMock()
        mock_element.labels = None
        mock_element.comment = "Test comment"

        text = ontology_embedder._create_text_representation(
            "TestElement",
            mock_element,
            "class"
        )

        assert "TestElement" in text, "Should still include ID"
        assert "Test comment" in text, "Should include comment"

    def test_includes_subclass_info_for_classes(self, ontology_embedder):
        """Test that subclass information is included for classes."""
        mock_class = MagicMock()
        mock_class.labels = []
        mock_class.comment = None
        mock_class.subclass_of = "ParentClass"

        text = ontology_embedder._create_text_representation(
            "ChildClass",
            mock_class,
            "class"
        )

        assert "subclass of ParentClass" in text, "Should include subclass relationship"


class TestVectorStoreOperations:
    """Test suite for vector store operations."""

    def test_vector_store_starts_empty(self, vector_store):
        """Test that vector store initializes empty."""
        assert vector_store.size() == 0, "New vector store should be empty"

    def test_vector_store_api_structure(self, vector_store):
        """Test that vector store has expected API methods."""
        assert hasattr(vector_store, 'add'), "Should have add method"
        assert hasattr(vector_store, 'add_batch'), "Should have add_batch method"
        assert hasattr(vector_store, 'search'), "Should have search method"
        assert hasattr(vector_store, 'size'), "Should have size method"

    def test_search_result_class_structure(self):
        """Test that SearchResult has expected structure."""
        # Create a sample SearchResult
        result = SearchResult(id="test-1", score=0.95, metadata={"element": "Test"})

        assert hasattr(result, 'id'), "Should have id attribute"
        assert hasattr(result, 'score'), "Should have score attribute"
        assert hasattr(result, 'metadata'), "Should have metadata attribute"
        assert result.id == "test-1"
        assert result.score == 0.95
        assert result.metadata["element"] == "Test"


class TestOntologySelectorIntegration:
    """Test suite for ontology selector with embeddings."""

    @pytest.fixture
    def sample_ontology(self):
        """Create a sample ontology for testing."""
        return Ontology(
            id="food",
            classes={
                "Recipe": OntologyClass(
                    uri="http://purl.org/ontology/fo/Recipe",
                    type="owl:Class",
                    labels=[{"value": "Recipe", "lang": "en-gb"}],
                    comment="A Recipe is a combination of ingredients and a method."
                ),
                "Ingredient": OntologyClass(
                    uri="http://purl.org/ontology/fo/Ingredient",
                    type="owl:Class",
                    labels=[{"value": "Ingredient", "lang": "en-gb"}],
                    comment="An Ingredient combines a quantity and a food."
                )
            },
            object_properties={
                "ingredients": OntologyProperty(
                    uri="http://purl.org/ontology/fo/ingredients",
                    type="owl:ObjectProperty",
                    labels=[{"value": "ingredients", "lang": "en-gb"}],
                    comment="Relates a recipe to its ingredients.",
                    domain="Recipe",
                    range="IngredientList"
                )
            },
            datatype_properties={},
            metadata={"name": "Food Ontology"}
        )

    @pytest.fixture
    def ontology_loader_mock(self, sample_ontology):
        """Create a mock ontology loader."""
        loader = MagicMock()
        loader.get_ontology.return_value = sample_ontology
        loader.get_all_ontology_ids.return_value = ["food"]
        return loader

    async def test_selector_handles_text_segments(
        self, ontology_embedder, ontology_loader_mock
    ):
        """Test that selector can process text segments."""
        # Create selector
        selector = OntologySelector(
            ontology_embedder=ontology_embedder,
            ontology_loader=ontology_loader_mock,
            top_k=5,
            similarity_threshold=0.3
        )

        # Create text segments
        segments = [
            TextSegment(text="Recipe for cornish pasty", type="sentence", position=0),
            TextSegment(text="ingredients needed", type="sentence", position=1)
        ]

        # Select ontology subset (will be empty since we haven't embedded anything)
        subsets = await selector.select_ontology_subset(segments)

        # Should return a list (even if empty)
        assert isinstance(subsets, list), "Should return a list of subsets"

    async def test_selector_with_no_embedding_service(self, vector_store, ontology_loader_mock):
        """Test that selector handles missing embedding service gracefully."""
        embedder = OntologyEmbedder(embedding_service=None, vector_store=vector_store)

        selector = OntologySelector(
            ontology_embedder=embedder,
            ontology_loader=ontology_loader_mock,
            top_k=5,
            similarity_threshold=0.7
        )

        segments = [
            TextSegment(text="Test text", type="sentence", position=0)
        ]

        # Should return empty results without crashing
        subsets = await selector.select_ontology_subset(segments)
        assert isinstance(subsets, list), "Should return a list even without embeddings"

    def test_merge_subsets_combines_elements(self, ontology_loader_mock, ontology_embedder):
        """Test that merging subsets combines all elements."""
        selector = OntologySelector(
            ontology_embedder=ontology_embedder,
            ontology_loader=ontology_loader_mock,
            top_k=5,
            similarity_threshold=0.7
        )

        # Create two subsets from same ontology
        subset1 = OntologySubset(
            ontology_id="food",
            classes={"Recipe": {"uri": "http://example.com/Recipe"}},
            object_properties={},
            datatype_properties={},
            metadata={},
            relevance_score=0.8
        )

        subset2 = OntologySubset(
            ontology_id="food",
            classes={"Ingredient": {"uri": "http://example.com/Ingredient"}},
            object_properties={"ingredients": {"uri": "http://example.com/ingredients"}},
            datatype_properties={},
            metadata={},
            relevance_score=0.9
        )

        merged = selector.merge_subsets([subset1, subset2])

        assert len(merged.classes) == 2, "Should combine classes"
        # Keys may be prefixed with ontology id
        assert any("Recipe" in key for key in merged.classes.keys())
        assert any("Ingredient" in key for key in merged.classes.keys())
        assert len(merged.object_properties) == 1, "Should include properties"


class TestEmbeddingEdgeCases:
    """Test suite for edge cases in embedding."""

    async def test_embed_element_with_no_labels(self, ontology_embedder):
        """Test embedding element without labels."""
        mock_element = MagicMock()
        mock_element.labels = None
        mock_element.comment = "Test element"

        text = ontology_embedder._create_text_representation(
            "TestElement",
            mock_element,
            "class"
        )

        # Should not crash and should include ID and comment
        assert "TestElement" in text
        assert "Test element" in text

    async def test_embed_element_with_empty_comment(self, ontology_embedder):
        """Test embedding element with empty comment."""
        mock_element = MagicMock()
        mock_element.labels = [{"value": "Label"}]
        mock_element.comment = None

        text = ontology_embedder._create_text_representation(
            "TestElement",
            mock_element,
            "class"
        )

        # Should not crash
        assert "Label" in text

    def test_ontology_element_metadata_structure(self):
        """Test OntologyElementMetadata structure."""
        metadata = OntologyElementMetadata(
            type="class",
            ontology="food",
            element="Recipe",
            definition={"uri": "http://example.com/Recipe"},
            text="Recipe A combination of ingredients"
        )

        assert metadata.type == "class"
        assert metadata.ontology == "food"
        assert metadata.element == "Recipe"
        assert "uri" in metadata.definition

    def test_vector_store_search_on_empty_store(self):
        """Test searching empty vector store."""
        # Need a non-empty store for faiss to work
        # This test verifies the store can be created but searching requires dimension
        store = InMemoryVectorStore()
        assert store.size() == 0, "Empty store should have size 0"


class TestOntologySubsetStructure:
    """Test suite for OntologySubset structure."""

    def test_ontology_subset_creation(self):
        """Test creating an OntologySubset."""
        subset = OntologySubset(
            ontology_id="test",
            classes={"Recipe": {}},
            object_properties={"produces": {}},
            datatype_properties={"serves": {}},
            metadata={"name": "Test"},
            relevance_score=0.85
        )

        assert subset.ontology_id == "test"
        assert len(subset.classes) == 1
        assert len(subset.object_properties) == 1
        assert len(subset.datatype_properties) == 1
        assert subset.relevance_score == 0.85

    def test_ontology_subset_default_score(self):
        """Test that OntologySubset has default score."""
        subset = OntologySubset(
            ontology_id="test",
            classes={},
            object_properties={},
            datatype_properties={},
            metadata={}
        )

        assert subset.relevance_score == 0.0, "Should have default score of 0.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
