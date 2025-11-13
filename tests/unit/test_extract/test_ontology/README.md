# Ontology Extractor Unit Tests

Comprehensive unit tests for the OntoRAG ontology extraction system.

## Test Coverage

### 1. `test_ontology_selector.py` - Auto-Include Properties Feature

Tests the critical dependency resolution that automatically includes all properties related to selected classes.

**Key Tests:**
- `test_auto_include_properties_for_recipe_class` - Verifies Recipe class auto-includes `ingredients`, `method`, `produces`, `serves`
- `test_auto_include_properties_for_ingredient_class` - Verifies Ingredient class auto-includes `food` property
- `test_auto_include_properties_for_range_class` - Tests properties are included when class appears in range
- `test_auto_include_adds_domain_and_range_classes` - Ensures related classes are added too
- `test_multiple_classes_get_all_related_properties` - Tests combining multiple class selections
- `test_no_duplicate_properties_added` - Ensures properties aren't duplicated

### 2. `test_uri_expansion.py` - URI Expansion

Tests that URIs are properly expanded using ontology definitions instead of constructed fallback URIs.

**Key Tests:**
- `test_expand_class_uri_from_ontology` - Class names expand to ontology URIs
- `test_expand_object_property_uri_from_ontology` - Object properties use ontology URIs
- `test_expand_datatype_property_uri_from_ontology` - Datatype properties use ontology URIs
- `test_expand_rdf_prefix` - Standard RDF prefixes expand correctly
- `test_expand_rdfs_prefix`, `test_expand_owl_prefix`, `test_expand_xsd_prefix` - Other standard prefixes
- `test_fallback_uri_for_instance` - Entity instances get constructed URIs
- `test_already_full_uri_unchanged` - Full URIs pass through
- `test_dict_access_not_object_attribute` - **Critical test** verifying dict access works (not object attributes)

## Running the Tests

### Run all ontology extractor tests:
```bash
cd /home/mark/work/trustgraph.ai/trustgraph
pytest tests/unit/test_extract/test_ontology/ -v
```

### Run specific test file:
```bash
pytest tests/unit/test_extract/test_ontology/test_ontology_selector.py -v
pytest tests/unit/test_extract/test_ontology/test_uri_expansion.py -v
```

### Run specific test:
```bash
pytest tests/unit/test_extract/test_ontology/test_ontology_selector.py::TestOntologySelector::test_auto_include_properties_for_recipe_class -v
```

### Run with coverage:
```bash
pytest tests/unit/test_extract/test_ontology/ --cov=trustgraph.extract.kg.ontology --cov-report=html
```

## Test Fixtures

- `sample_ontology` - Complete Food Ontology with Recipe, Ingredient, Food, Method classes
- `ontology_loader_with_sample` - Mock OntologyLoader with the sample ontology
- `ontology_embedder` - Mock embedder for testing
- `extractor` - KgExtractOntology instance for URI expansion tests
- `ontology_subset_with_uris` - OntologySubset with proper URIs defined

## Implementation Notes

These tests verify the fixes made to address:
1. **Disconnected graph problem** - Auto-include properties feature ensures all relevant relationships are available
2. **Wrong URIs problem** - URI expansion using ontology definitions instead of constructed fallbacks
3. **Dict vs object attribute problem** - URI expansion works with dicts (from `cls.__dict__`) not object attributes
