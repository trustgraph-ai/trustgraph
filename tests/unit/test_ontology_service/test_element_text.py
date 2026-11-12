"""
Unit tests for Processor._element_text — builds the embedding text
representation for an ontology element.
"""

import pytest
from trustgraph.ontology.service import OntologyElement, Processor


class TestElementText:

    def test_class_basic(self):
        elem = OntologyElement(
            element_id="Recipe",
            element_type="class",
            uri="http://example.org/Recipe",
            labels=[{"value": "Recipe", "lang": "en"}],
            comment="A combination of ingredients.",
        )
        text = Processor._element_text("Recipe", elem)
        assert "Recipe" in text
        assert "A combination of ingredients." in text

    def test_class_with_subclass(self):
        elem = OntologyElement(
            element_id="ItalianRecipe",
            element_type="class",
            uri="http://example.org/ItalianRecipe",
            subclass_of="Recipe",
        )
        text = Processor._element_text("ItalianRecipe", elem)
        assert "subclass of Recipe" in text

    def test_property_with_domain_range(self):
        elem = OntologyElement(
            element_id="ingredients",
            element_type="objectProperty",
            uri="http://example.org/ingredients",
            domain="Recipe",
            range="Food",
        )
        text = Processor._element_text("ingredients", elem)
        assert "domain: Recipe" in text
        assert "range: Food" in text

    def test_datatype_property_domain_range(self):
        elem = OntologyElement(
            element_id="serves",
            element_type="datatypeProperty",
            uri="http://example.org/serves",
            domain="Recipe",
            range="integer",
        )
        text = Processor._element_text("serves", elem)
        assert "domain: Recipe" in text
        assert "range: integer" in text

    def test_hyphens_and_underscores_replaced(self):
        elem = OntologyElement(
            element_id="has-primary_ingredient",
            element_type="objectProperty",
            uri="http://example.org/has-primary_ingredient",
        )
        text = Processor._element_text("has-primary_ingredient", elem)
        assert "has primary ingredient" in text
        assert "-" not in text.split()[0:3]

    def test_multiple_labels(self):
        elem = OntologyElement(
            element_id="Recipe",
            element_type="class",
            uri="http://example.org/Recipe",
            labels=[
                {"value": "Recipe", "lang": "en"},
                {"value": "Recette", "lang": "fr"},
            ],
        )
        text = Processor._element_text("Recipe", elem)
        assert "Recipe" in text
        assert "Recette" in text

    def test_class_does_not_include_domain_range(self):
        elem = OntologyElement(
            element_id="Recipe",
            element_type="class",
            uri="http://example.org/Recipe",
            domain="ShouldNotAppear",
            range="ShouldNotAppear",
        )
        text = Processor._element_text("Recipe", elem)
        assert "domain:" not in text
        assert "range:" not in text

    def test_property_does_not_include_subclass(self):
        elem = OntologyElement(
            element_id="ingredients",
            element_type="objectProperty",
            uri="http://example.org/ingredients",
            subclass_of="ShouldNotAppear",
        )
        text = Processor._element_text("ingredients", elem)
        assert "subclass of" not in text

    def test_empty_element(self):
        elem = OntologyElement(
            element_id="X",
            element_type="class",
            uri="http://example.org/X",
        )
        text = Processor._element_text("X", elem)
        assert text.strip() == "X"
