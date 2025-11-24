"""
Unit tests for OntologySelector component.

Tests the critical auto-include properties feature that automatically pulls in
all properties related to selected classes.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from trustgraph.extract.kg.ontology.ontology_selector import (
    OntologySelector,
    OntologySubset
)
from trustgraph.extract.kg.ontology.ontology_loader import (
    Ontology,
    OntologyClass,
    OntologyProperty
)
from trustgraph.extract.kg.ontology.text_processor import TextSegment


@pytest.fixture
def sample_ontology():
    """Create a sample food ontology for testing."""
    # Create classes
    recipe_class = OntologyClass(
        uri="http://purl.org/ontology/fo/Recipe",
        type="owl:Class",
        labels=[{"value": "Recipe", "lang": "en-gb"}],
        comment="A Recipe is a combination of ingredients and a method."
    )

    ingredient_class = OntologyClass(
        uri="http://purl.org/ontology/fo/Ingredient",
        type="owl:Class",
        labels=[{"value": "Ingredient", "lang": "en-gb"}],
        comment="An Ingredient is a combination of a quantity and a food."
    )

    food_class = OntologyClass(
        uri="http://purl.org/ontology/fo/Food",
        type="owl:Class",
        labels=[{"value": "Food", "lang": "en-gb"}],
        comment="A Food is something that can be eaten."
    )

    method_class = OntologyClass(
        uri="http://purl.org/ontology/fo/Method",
        type="owl:Class",
        labels=[{"value": "Method", "lang": "en-gb"}],
        comment="A Method is the way in which ingredients are combined."
    )

    # Create object properties
    ingredients_prop = OntologyProperty(
        uri="http://purl.org/ontology/fo/ingredients",
        type="owl:ObjectProperty",
        labels=[{"value": "ingredients", "lang": "en-gb"}],
        comment="The ingredients property relates a recipe to an ingredient list.",
        domain="Recipe",
        range="IngredientList"
    )

    food_prop = OntologyProperty(
        uri="http://purl.org/ontology/fo/food",
        type="owl:ObjectProperty",
        labels=[{"value": "food", "lang": "en-gb"}],
        comment="The food property relates an ingredient to the food that is required.",
        domain="Ingredient",
        range="Food"
    )

    method_prop = OntologyProperty(
        uri="http://purl.org/ontology/fo/method",
        type="owl:ObjectProperty",
        labels=[{"value": "method", "lang": "en-gb"}],
        comment="The method property relates a recipe to the method used.",
        domain="Recipe",
        range="Method"
    )

    produces_prop = OntologyProperty(
        uri="http://purl.org/ontology/fo/produces",
        type="owl:ObjectProperty",
        labels=[{"value": "produces", "lang": "en-gb"}],
        comment="The produces property relates a recipe to the food it produces.",
        domain="Recipe",
        range="Food"
    )

    # Create datatype properties
    serves_prop = OntologyProperty(
        uri="http://purl.org/ontology/fo/serves",
        type="owl:DatatypeProperty",
        labels=[{"value": "serves", "lang": "en-gb"}],
        comment="The serves property indicates what the recipe is intended to serve.",
        domain="Recipe",
        range="xsd:string"
    )

    # Build ontology
    ontology = Ontology(
        id="food",
        metadata={
            "name": "Food Ontology",
            "namespace": "http://purl.org/ontology/fo/"
        },
        classes={
            "Recipe": recipe_class,
            "Ingredient": ingredient_class,
            "Food": food_class,
            "Method": method_class
        },
        object_properties={
            "ingredients": ingredients_prop,
            "food": food_prop,
            "method": method_prop,
            "produces": produces_prop
        },
        datatype_properties={
            "serves": serves_prop
        }
    )

    return ontology


@pytest.fixture
def ontology_loader_with_sample(sample_ontology):
    """Create an OntologyLoader with the sample ontology."""
    loader = Mock()
    loader.get_ontology = Mock(return_value=sample_ontology)
    loader.ontologies = {"food": sample_ontology}
    return loader


@pytest.fixture
def ontology_embedder():
    """Create a mock OntologyEmbedder."""
    embedder = Mock()
    embedder.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])  # Mock embedding

    # Mock vector store with search results
    vector_store = Mock()
    embedder.get_vector_store = Mock(return_value=vector_store)

    return embedder


class TestOntologySelector:
    """Test suite for OntologySelector."""

    def test_auto_include_properties_for_recipe_class(
        self, ontology_loader_with_sample, ontology_embedder, sample_ontology
    ):
        """Test that selecting Recipe class automatically includes all related properties."""
        selector = OntologySelector(
            ontology_embedder=ontology_embedder,
            ontology_loader=ontology_loader_with_sample,
            top_k=10,
            similarity_threshold=0.3
        )

        # Create a subset with only Recipe class initially selected
        subset = OntologySubset(
            ontology_id="food",
            classes={"Recipe": sample_ontology.classes["Recipe"].__dict__},
            object_properties={},
            datatype_properties={},
            metadata=sample_ontology.metadata,
            relevance_score=0.8
        )

        # Resolve dependencies (this is where auto-include happens)
        selector._resolve_dependencies(subset)

        # Assert that properties with Recipe in domain are included
        assert "ingredients" in subset.object_properties, \
            "ingredients property should be auto-included (Recipe in domain)"
        assert "method" in subset.object_properties, \
            "method property should be auto-included (Recipe in domain)"
        assert "produces" in subset.object_properties, \
            "produces property should be auto-included (Recipe in domain)"
        assert "serves" in subset.datatype_properties, \
            "serves property should be auto-included (Recipe in domain)"

        # Assert that unrelated property is NOT included
        assert "food" not in subset.object_properties, \
            "food property should NOT be included (Recipe not in domain/range)"

    def test_auto_include_properties_for_ingredient_class(
        self, ontology_loader_with_sample, ontology_embedder, sample_ontology
    ):
        """Test that selecting Ingredient class includes properties with Ingredient in domain."""
        selector = OntologySelector(
            ontology_embedder=ontology_embedder,
            ontology_loader=ontology_loader_with_sample
        )

        subset = OntologySubset(
            ontology_id="food",
            classes={"Ingredient": sample_ontology.classes["Ingredient"].__dict__},
            object_properties={},
            datatype_properties={},
            metadata=sample_ontology.metadata
        )

        selector._resolve_dependencies(subset)

        # Ingredient has 'food' property in domain
        assert "food" in subset.object_properties, \
            "food property should be auto-included (Ingredient in domain)"

        # Recipe-related properties should NOT be included
        assert "ingredients" not in subset.object_properties
        assert "method" not in subset.object_properties

    def test_auto_include_properties_for_range_class(
        self, ontology_loader_with_sample, ontology_embedder, sample_ontology
    ):
        """Test that selecting a class includes properties with that class in range."""
        selector = OntologySelector(
            ontology_embedder=ontology_embedder,
            ontology_loader=ontology_loader_with_sample
        )

        subset = OntologySubset(
            ontology_id="food",
            classes={"Food": sample_ontology.classes["Food"].__dict__},
            object_properties={},
            datatype_properties={},
            metadata=sample_ontology.metadata
        )

        selector._resolve_dependencies(subset)

        # Food appears in range of 'food' and 'produces' properties
        assert "food" in subset.object_properties, \
            "food property should be auto-included (Food in range)"
        assert "produces" in subset.object_properties, \
            "produces property should be auto-included (Food in range)"

    def test_auto_include_adds_domain_and_range_classes(
        self, ontology_loader_with_sample, ontology_embedder, sample_ontology
    ):
        """Test that auto-included properties also add their domain/range classes."""
        selector = OntologySelector(
            ontology_embedder=ontology_embedder,
            ontology_loader=ontology_loader_with_sample
        )

        # Start with only Recipe class
        subset = OntologySubset(
            ontology_id="food",
            classes={"Recipe": sample_ontology.classes["Recipe"].__dict__},
            object_properties={},
            datatype_properties={},
            metadata=sample_ontology.metadata
        )

        selector._resolve_dependencies(subset)

        # Should auto-include 'produces' property (Recipe → Food)
        assert "produces" in subset.object_properties

        # Should also add Food class (range of produces)
        assert "Food" in subset.classes, \
            "Food class should be added (range of auto-included produces property)"

        # Should also add Method class (range of method property)
        assert "Method" in subset.classes, \
            "Method class should be added (range of auto-included method property)"

    def test_multiple_classes_get_all_related_properties(
        self, ontology_loader_with_sample, ontology_embedder, sample_ontology
    ):
        """Test that selecting multiple classes includes all their related properties."""
        selector = OntologySelector(
            ontology_embedder=ontology_embedder,
            ontology_loader=ontology_loader_with_sample
        )

        # Select both Recipe and Ingredient classes
        subset = OntologySubset(
            ontology_id="food",
            classes={
                "Recipe": sample_ontology.classes["Recipe"].__dict__,
                "Ingredient": sample_ontology.classes["Ingredient"].__dict__
            },
            object_properties={},
            datatype_properties={},
            metadata=sample_ontology.metadata
        )

        selector._resolve_dependencies(subset)

        # Should include Recipe-related properties
        assert "ingredients" in subset.object_properties
        assert "method" in subset.object_properties
        assert "produces" in subset.object_properties
        assert "serves" in subset.datatype_properties

        # Should also include Ingredient-related properties
        assert "food" in subset.object_properties

    def test_no_duplicate_properties_added(
        self, ontology_loader_with_sample, ontology_embedder, sample_ontology
    ):
        """Test that properties aren't added multiple times."""
        selector = OntologySelector(
            ontology_embedder=ontology_embedder,
            ontology_loader=ontology_loader_with_sample
        )

        # Start with Recipe and Food (both related to 'produces')
        subset = OntologySubset(
            ontology_id="food",
            classes={
                "Recipe": sample_ontology.classes["Recipe"].__dict__,
                "Food": sample_ontology.classes["Food"].__dict__
            },
            object_properties={},
            datatype_properties={},
            metadata=sample_ontology.metadata
        )

        selector._resolve_dependencies(subset)

        # 'produces' should be included once (not duplicated)
        assert "produces" in subset.object_properties
        # Count would be 1 - dict keys are unique, so this is guaranteed
        # but worth documenting the expected behavior


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
