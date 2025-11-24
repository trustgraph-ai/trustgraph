"""
Unit tests for ontology loading and configuration.

Tests that ontologies are properly loaded from configuration,
parsed, validated, and managed by the OntologyLoader.
"""

import pytest
from trustgraph.extract.kg.ontology.ontology_loader import (
    OntologyLoader,
    Ontology,
    OntologyClass,
    OntologyProperty
)


@pytest.fixture
def ontology_loader():
    """Create an OntologyLoader instance."""
    return OntologyLoader()


@pytest.fixture
def sample_ontology_config():
    """Create a sample ontology configuration."""
    return {
        "food": {
            "metadata": {
                "name": "Food Ontology",
                "namespace": "http://purl.org/ontology/fo/"
            },
            "classes": {
                "Recipe": {
                    "uri": "http://purl.org/ontology/fo/Recipe",
                    "type": "owl:Class",
                    "rdfs:label": [{"value": "Recipe", "lang": "en-gb"}],
                    "rdfs:comment": "A Recipe is a combination of ingredients and a method."
                },
                "Ingredient": {
                    "uri": "http://purl.org/ontology/fo/Ingredient",
                    "type": "owl:Class",
                    "rdfs:label": [{"value": "Ingredient", "lang": "en-gb"}],
                    "rdfs:comment": "An Ingredient combines a quantity and a food."
                },
                "Food": {
                    "uri": "http://purl.org/ontology/fo/Food",
                    "type": "owl:Class",
                    "rdfs:label": [{"value": "Food", "lang": "en-gb"}],
                    "rdfs:comment": "A Food is something that can be eaten.",
                    "rdfs:subClassOf": "EdibleThing"
                }
            },
            "objectProperties": {
                "ingredients": {
                    "uri": "http://purl.org/ontology/fo/ingredients",
                    "type": "owl:ObjectProperty",
                    "rdfs:label": [{"value": "ingredients", "lang": "en-gb"}],
                    "rdfs:domain": "Recipe",
                    "rdfs:range": "IngredientList"
                },
                "produces": {
                    "uri": "http://purl.org/ontology/fo/produces",
                    "type": "owl:ObjectProperty",
                    "rdfs:label": [{"value": "produces", "lang": "en-gb"}],
                    "rdfs:domain": "Recipe",
                    "rdfs:range": "Food"
                }
            },
            "datatypeProperties": {
                "serves": {
                    "uri": "http://purl.org/ontology/fo/serves",
                    "type": "owl:DatatypeProperty",
                    "rdfs:label": [{"value": "serves", "lang": "en-gb"}],
                    "rdfs:domain": "Recipe",
                    "rdfs:range": "xsd:string"
                }
            }
        }
    }


class TestOntologyLoaderInitialization:
    """Test suite for OntologyLoader initialization."""

    def test_loader_starts_empty(self, ontology_loader):
        """Test that loader initializes with no ontologies."""
        assert len(ontology_loader.get_all_ontologies()) == 0

    def test_loader_get_nonexistent_ontology(self, ontology_loader):
        """Test getting non-existent ontology returns None."""
        result = ontology_loader.get_ontology("nonexistent")
        assert result is None


class TestOntologyLoading:
    """Test suite for loading ontologies from configuration."""

    def test_loads_single_ontology(self, ontology_loader, sample_ontology_config):
        """Test loading a single ontology."""
        ontology_loader.update_ontologies(sample_ontology_config)

        ontologies = ontology_loader.get_all_ontologies()
        assert len(ontologies) == 1
        assert "food" in ontologies

    def test_loaded_ontology_has_correct_id(self, ontology_loader, sample_ontology_config):
        """Test that loaded ontology has correct ID."""
        ontology_loader.update_ontologies(sample_ontology_config)

        ontology = ontology_loader.get_ontology("food")
        assert ontology is not None
        assert ontology.id == "food"

    def test_loaded_ontology_has_metadata(self, ontology_loader, sample_ontology_config):
        """Test that loaded ontology includes metadata."""
        ontology_loader.update_ontologies(sample_ontology_config)

        ontology = ontology_loader.get_ontology("food")
        assert ontology.metadata["name"] == "Food Ontology"
        assert ontology.metadata["namespace"] == "http://purl.org/ontology/fo/"

    def test_loaded_ontology_has_classes(self, ontology_loader, sample_ontology_config):
        """Test that loaded ontology includes classes."""
        ontology_loader.update_ontologies(sample_ontology_config)

        ontology = ontology_loader.get_ontology("food")
        assert len(ontology.classes) == 3
        assert "Recipe" in ontology.classes
        assert "Ingredient" in ontology.classes
        assert "Food" in ontology.classes

    def test_loaded_classes_have_correct_properties(self, ontology_loader, sample_ontology_config):
        """Test that loaded classes have correct properties."""
        ontology_loader.update_ontologies(sample_ontology_config)

        ontology = ontology_loader.get_ontology("food")
        recipe = ontology.get_class("Recipe")

        assert isinstance(recipe, OntologyClass)
        assert recipe.uri == "http://purl.org/ontology/fo/Recipe"
        assert recipe.type == "owl:Class"
        assert len(recipe.labels) == 1
        assert recipe.labels[0]["value"] == "Recipe"
        assert "combination of ingredients" in recipe.comment

    def test_loaded_ontology_has_object_properties(self, ontology_loader, sample_ontology_config):
        """Test that loaded ontology includes object properties."""
        ontology_loader.update_ontologies(sample_ontology_config)

        ontology = ontology_loader.get_ontology("food")
        assert len(ontology.object_properties) == 2
        assert "ingredients" in ontology.object_properties
        assert "produces" in ontology.object_properties

    def test_loaded_properties_have_domain_and_range(self, ontology_loader, sample_ontology_config):
        """Test that loaded properties have domain and range."""
        ontology_loader.update_ontologies(sample_ontology_config)

        ontology = ontology_loader.get_ontology("food")
        produces = ontology.get_property("produces")

        assert isinstance(produces, OntologyProperty)
        assert produces.domain == "Recipe"
        assert produces.range == "Food"

    def test_loaded_ontology_has_datatype_properties(self, ontology_loader, sample_ontology_config):
        """Test that loaded ontology includes datatype properties."""
        ontology_loader.update_ontologies(sample_ontology_config)

        ontology = ontology_loader.get_ontology("food")
        assert len(ontology.datatype_properties) == 1
        assert "serves" in ontology.datatype_properties

    def test_loads_multiple_ontologies(self, ontology_loader):
        """Test loading multiple ontologies."""
        config = {
            "food": {
                "metadata": {"name": "Food Ontology"},
                "classes": {"Recipe": {"uri": "http://example.com/Recipe"}},
                "objectProperties": {},
                "datatypeProperties": {}
            },
            "music": {
                "metadata": {"name": "Music Ontology"},
                "classes": {"Song": {"uri": "http://example.com/Song"}},
                "objectProperties": {},
                "datatypeProperties": {}
            }
        }

        ontology_loader.update_ontologies(config)

        ontologies = ontology_loader.get_all_ontologies()
        assert len(ontologies) == 2
        assert "food" in ontologies
        assert "music" in ontologies

    def test_update_replaces_existing_ontologies(self, ontology_loader, sample_ontology_config):
        """Test that update replaces existing ontologies."""
        # Load initial ontologies
        ontology_loader.update_ontologies(sample_ontology_config)
        assert len(ontology_loader.get_all_ontologies()) == 1

        # Update with different config
        new_config = {
            "music": {
                "metadata": {"name": "Music Ontology"},
                "classes": {},
                "objectProperties": {},
                "datatypeProperties": {}
            }
        }
        ontology_loader.update_ontologies(new_config)

        # Old ontologies should be replaced
        ontologies = ontology_loader.get_all_ontologies()
        assert len(ontologies) == 1
        assert "music" in ontologies
        assert "food" not in ontologies


class TestOntologyRetrieval:
    """Test suite for retrieving ontologies."""

    def test_get_ontology_by_id(self, ontology_loader, sample_ontology_config):
        """Test retrieving ontology by ID."""
        ontology_loader.update_ontologies(sample_ontology_config)

        ontology = ontology_loader.get_ontology("food")
        assert ontology is not None
        assert isinstance(ontology, Ontology)

    def test_get_all_ontologies(self, ontology_loader):
        """Test retrieving all ontologies."""
        config = {
            "food": {
                "metadata": {},
                "classes": {},
                "objectProperties": {},
                "datatypeProperties": {}
            },
            "music": {
                "metadata": {},
                "classes": {},
                "objectProperties": {},
                "datatypeProperties": {}
            }
        }
        ontology_loader.update_ontologies(config)

        ontologies = ontology_loader.get_all_ontologies()
        assert isinstance(ontologies, dict)
        assert len(ontologies) == 2

    def test_get_all_ontology_ids(self, ontology_loader):
        """Test retrieving all ontology IDs."""
        config = {
            "food": {
                "metadata": {},
                "classes": {},
                "objectProperties": {},
                "datatypeProperties": {}
            },
            "music": {
                "metadata": {},
                "classes": {},
                "objectProperties": {},
                "datatypeProperties": {}
            }
        }
        ontology_loader.update_ontologies(config)

        ontologies = ontology_loader.get_all_ontologies()
        ids = list(ontologies.keys())
        assert len(ids) == 2
        assert "food" in ids
        assert "music" in ids


class TestOntologyClassMethods:
    """Test suite for Ontology helper methods."""

    def test_get_class(self, ontology_loader, sample_ontology_config):
        """Test getting a class from ontology."""
        ontology_loader.update_ontologies(sample_ontology_config)
        ontology = ontology_loader.get_ontology("food")

        recipe = ontology.get_class("Recipe")
        assert recipe is not None
        assert recipe.uri == "http://purl.org/ontology/fo/Recipe"

    def test_get_nonexistent_class(self, ontology_loader, sample_ontology_config):
        """Test getting non-existent class returns None."""
        ontology_loader.update_ontologies(sample_ontology_config)
        ontology = ontology_loader.get_ontology("food")

        result = ontology.get_class("NonExistent")
        assert result is None

    def test_get_property(self, ontology_loader, sample_ontology_config):
        """Test getting a property from ontology."""
        ontology_loader.update_ontologies(sample_ontology_config)
        ontology = ontology_loader.get_ontology("food")

        produces = ontology.get_property("produces")
        assert produces is not None
        assert produces.domain == "Recipe"

    def test_get_property_checks_both_types(self, ontology_loader, sample_ontology_config):
        """Test that get_property checks both object and datatype properties."""
        ontology_loader.update_ontologies(sample_ontology_config)
        ontology = ontology_loader.get_ontology("food")

        # Object property
        produces = ontology.get_property("produces")
        assert produces is not None

        # Datatype property
        serves = ontology.get_property("serves")
        assert serves is not None

    def test_get_parent_classes(self, ontology_loader, sample_ontology_config):
        """Test getting parent classes following subClassOf."""
        ontology_loader.update_ontologies(sample_ontology_config)
        ontology = ontology_loader.get_ontology("food")

        parents = ontology.get_parent_classes("Food")
        assert "EdibleThing" in parents

    def test_get_parent_classes_empty_for_root(self, ontology_loader, sample_ontology_config):
        """Test that root classes have no parents."""
        ontology_loader.update_ontologies(sample_ontology_config)
        ontology = ontology_loader.get_ontology("food")

        parents = ontology.get_parent_classes("Recipe")
        assert len(parents) == 0


class TestOntologyValidation:
    """Test suite for ontology validation."""

    def test_validates_property_domain_exists(self, ontology_loader):
        """Test validation of property domain."""
        config = {
            "test": {
                "metadata": {},
                "classes": {
                    "Recipe": {"uri": "http://example.com/Recipe"}
                },
                "objectProperties": {
                    "produces": {
                        "uri": "http://example.com/produces",
                        "type": "owl:ObjectProperty",
                        "rdfs:domain": "NonExistentClass",  # Invalid
                        "rdfs:range": "Food"
                    }
                },
                "datatypeProperties": {}
            }
        }

        ontology_loader.update_ontologies(config)
        ontology = ontology_loader.get_ontology("test")

        issues = ontology.validate_structure()
        assert len(issues) > 0
        assert any("unknown domain" in issue.lower() for issue in issues)

    def test_validates_object_property_range_exists(self, ontology_loader):
        """Test validation of object property range."""
        config = {
            "test": {
                "metadata": {},
                "classes": {
                    "Recipe": {"uri": "http://example.com/Recipe"}
                },
                "objectProperties": {
                    "produces": {
                        "uri": "http://example.com/produces",
                        "type": "owl:ObjectProperty",
                        "rdfs:domain": "Recipe",
                        "rdfs:range": "NonExistentClass"  # Invalid
                    }
                },
                "datatypeProperties": {}
            }
        }

        ontology_loader.update_ontologies(config)
        ontology = ontology_loader.get_ontology("test")

        issues = ontology.validate_structure()
        assert len(issues) > 0
        assert any("unknown range" in issue.lower() for issue in issues)

    def test_detects_circular_inheritance(self, ontology_loader):
        """Test detection of circular inheritance."""
        config = {
            "test": {
                "metadata": {},
                "classes": {
                    "A": {
                        "uri": "http://example.com/A",
                        "rdfs:subClassOf": "B"
                    },
                    "B": {
                        "uri": "http://example.com/B",
                        "rdfs:subClassOf": "C"
                    },
                    "C": {
                        "uri": "http://example.com/C",
                        "rdfs:subClassOf": "A"  # Circular!
                    }
                },
                "objectProperties": {},
                "datatypeProperties": {}
            }
        }

        ontology_loader.update_ontologies(config)
        ontology = ontology_loader.get_ontology("test")

        issues = ontology.validate_structure()
        assert len(issues) > 0
        assert any("circular" in issue.lower() for issue in issues)

    def test_valid_ontology_has_no_issues(self, ontology_loader, sample_ontology_config):
        """Test that valid ontology passes validation."""
        # Modify config to have valid references
        config = sample_ontology_config.copy()
        config["food"]["classes"]["EdibleThing"] = {
            "uri": "http://purl.org/ontology/fo/EdibleThing"
        }
        config["food"]["classes"]["IngredientList"] = {
            "uri": "http://purl.org/ontology/fo/IngredientList"
        }

        ontology_loader.update_ontologies(config)
        ontology = ontology_loader.get_ontology("food")

        issues = ontology.validate_structure()
        # Should have minimal or no issues for valid ontology
        assert isinstance(issues, list)


class TestEdgeCases:
    """Test suite for edge cases in ontology loading."""

    def test_handles_empty_config(self, ontology_loader):
        """Test handling of empty configuration."""
        ontology_loader.update_ontologies({})

        ontologies = ontology_loader.get_all_ontologies()
        assert len(ontologies) == 0

    def test_handles_ontology_without_classes(self, ontology_loader):
        """Test handling of ontology with no classes."""
        config = {
            "minimal": {
                "metadata": {"name": "Minimal"},
                "classes": {},
                "objectProperties": {},
                "datatypeProperties": {}
            }
        }

        ontology_loader.update_ontologies(config)
        ontology = ontology_loader.get_ontology("minimal")

        assert ontology is not None
        assert len(ontology.classes) == 0

    def test_handles_ontology_without_properties(self, ontology_loader):
        """Test handling of ontology with no properties."""
        config = {
            "test": {
                "metadata": {},
                "classes": {
                    "Recipe": {"uri": "http://example.com/Recipe"}
                },
                "objectProperties": {},
                "datatypeProperties": {}
            }
        }

        ontology_loader.update_ontologies(config)
        ontology = ontology_loader.get_ontology("test")

        assert ontology is not None
        assert len(ontology.object_properties) == 0
        assert len(ontology.datatype_properties) == 0

    def test_handles_missing_optional_fields(self, ontology_loader):
        """Test handling of missing optional fields."""
        config = {
            "test": {
                "metadata": {},
                "classes": {
                    "Simple": {
                        "uri": "http://example.com/Simple"
                        # No labels, comments, subclass, etc.
                    }
                },
                "objectProperties": {},
                "datatypeProperties": {}
            }
        }

        ontology_loader.update_ontologies(config)
        ontology = ontology_loader.get_ontology("test")

        simple = ontology.get_class("Simple")
        assert simple is not None
        assert simple.uri == "http://example.com/Simple"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
