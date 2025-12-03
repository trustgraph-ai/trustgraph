# Ontology Knowledge Extraction - Phase 2 Refactor

**Status**: Draft
**Author**: Analysis Session 2025-12-03
**Related**: `ontology.md`, `ontorag.md`

## Overview

This document identifies inconsistencies in the current ontology-based knowledge extraction system and proposes a refactor to improve LLM performance and reduce information loss.

## Current Implementation

### How It Works Now

1. **Ontology Loading** (`ontology_loader.py`)
   - Loads ontology JSON with keys like `"fo/Recipe"`, `"fo/Food"`, `"fo/produces"`
   - Class IDs include namespace prefix in the key itself
   - Example from `food.ontology`:
     ```json
     "classes": {
       "fo/Recipe": {
         "uri": "http://purl.org/ontology/fo/Recipe",
         "rdfs:comment": "A Recipe is a combination..."
       }
     }
     ```

2. **Prompt Construction** (`extract.py:299-307`, `ontology-prompt.md`)
   - Template receives `classes`, `object_properties`, `datatype_properties` dicts
   - Template iterates: `{% for class_id, class_def in classes.items() %}`
   - LLM sees: `**fo/Recipe**: A Recipe is a combination...`
   - Example output format shows:
     ```json
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
     {"subject": "recipe:cornish-pasty", "predicate": "has_ingredient", "object": "ingredient:flour"}
     ```

3. **Response Parsing** (`extract.py:382-428`)
   - Expects JSON array: `[{"subject": "...", "predicate": "...", "object": "..."}]`
   - Validates against ontology subset
   - Expands URIs via `expand_uri()` (extract.py:473-521)

4. **URI Expansion** (`extract.py:473-521`)
   - Checks if value is in `ontology_subset.classes` dict
   - If found, extracts URI from class definition
   - If not found, constructs URI: `f"https://trustgraph.ai/ontology/{ontology_id}#{value}"`

### Data Flow Example

**Ontology JSON → Loader → Prompt:**
```
"fo/Recipe" → classes["fo/Recipe"] → LLM sees "**fo/Recipe**"
```

**LLM → Parser → Output:**
```
"Recipe" → not in classes["fo/Recipe"] → constructs URI → LOSES original URI
"fo/Recipe" → found in classes → uses original URI → PRESERVES URI
```

## Problems Identified

### 1. **Inconsistent Examples in Prompt**

**Issue**: The prompt template shows class IDs with prefixes (`fo/Recipe`) but the example output uses unprefixed class names (`Recipe`).

**Location**: `ontology-prompt.md:5-52`

```markdown
## Ontology Classes:
- **fo/Recipe**: A Recipe is...

## Example Output:
{"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
```

**Impact**: LLM receives conflicting signals about what format to use.

### 2. **Information Loss in URI Expansion**

**Issue**: When LLM returns unprefixed class names following the example, `expand_uri()` can't find them in the ontology dict and constructs fallback URIs, losing the original proper URIs.

**Location**: `extract.py:494-500`

```python
if value in ontology_subset.classes:  # Looks for "Recipe"
    class_def = ontology_subset.classes[value]  # But key is "fo/Recipe"
    if isinstance(class_def, dict) and 'uri' in class_def:
        return class_def['uri']  # Never reached!
return f"https://trustgraph.ai/ontology/{ontology_id}#{value}"  # Fallback
```

**Impact**:
- Original URI: `http://purl.org/ontology/fo/Recipe`
- Constructed URI: `https://trustgraph.ai/ontology/food#Recipe`
- Semantic meaning lost, breaks interoperability

### 3. **Ambiguous Entity Instance Format**

**Issue**: No clear guidance on entity instance URI format.

**Examples in prompt**:
- `"recipe:cornish-pasty"` (namespace-like prefix)
- `"ingredient:flour"` (different prefix)

**Actual behavior** (extract.py:517-520):
```python
# Treat as entity instance - construct unique URI
normalized = value.replace(" ", "-").lower()
return f"https://trustgraph.ai/{ontology_id}/{normalized}"
```

**Impact**: LLM must guess prefixing convention with no ontology context.

### 4. **No Namespace Prefix Guidance**

**Issue**: The ontology JSON contains namespace definitions (line 10-25 in food.ontology):
```json
"namespaces": {
  "fo": "http://purl.org/ontology/fo/",
  "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
  ...
}
```

But these are never surfaced to the LLM. The LLM doesn't know:
- What "fo" means
- What prefix to use for entities
- Which namespace applies to which elements

### 5. **Labels Not Used in Prompt**

**Issue**: Every class has `rdfs:label` fields (e.g., `{"value": "Recipe", "lang": "en-gb"}`), but the prompt template doesn't use them.

**Current**: Shows only `class_id` and `comment`
```jinja
- **{{class_id}}**{% if class_def.comment %}: {{class_def.comment}}{% endif %}
```

**Available but unused**:
```python
"rdfs:label": [{"value": "Recipe", "lang": "en-gb"}]
```

**Impact**: Could provide human-readable names alongside technical IDs.

## Proposed Solutions

### Option A: Normalize to Unprefixed IDs

**Approach**: Strip prefixes from class IDs before showing to LLM.

**Changes**:
1. Modify `build_extraction_variables()` to transform keys:
   ```python
   classes_for_prompt = {
       k.split('/')[-1]: v  # "fo/Recipe" → "Recipe"
       for k, v in ontology_subset.classes.items()
   }
   ```

2. Update prompt example to match (already uses unprefixed names)

3. Modify `expand_uri()` to handle both formats:
   ```python
   # Try exact match first
   if value in ontology_subset.classes:
       return ontology_subset.classes[value]['uri']

   # Try with prefix
   for prefix in ['fo/', 'rdf:', 'rdfs:']:
       prefixed = f"{prefix}{value}"
       if prefixed in ontology_subset.classes:
           return ontology_subset.classes[prefixed]['uri']
   ```

**Pros**:
- Cleaner, more human-readable
- Matches existing prompt examples
- LLMs work better with simpler tokens

**Cons**:
- Class name collisions if multiple ontologies have same class name
- Loses namespace information
- Requires fallback logic for lookups

### Option B: Use Full Prefixed IDs Consistently

**Approach**: Update examples to use prefixed IDs matching what's shown in the class list.

**Changes**:
1. Update prompt example (ontology-prompt.md:46-52):
   ```json
   [
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "fo/Recipe"},
     {"subject": "recipe:cornish-pasty", "predicate": "rdfs:label", "object": "Cornish Pasty"},
     {"subject": "recipe:cornish-pasty", "predicate": "fo/produces", "object": "food:cornish-pasty"},
     {"subject": "food:cornish-pasty", "predicate": "rdf:type", "object": "fo/Food"}
   ]
   ```

2. Add namespace explanation to prompt:
   ```markdown
   ## Namespace Prefixes:
   - **fo/**: Food Ontology (http://purl.org/ontology/fo/)
   - **rdf:**: RDF Schema
   - **rdfs:**: RDF Schema

   Use these prefixes exactly as shown when referencing classes and properties.
   ```

3. Keep `expand_uri()` as-is (works correctly when matches found)

**Pros**:
- Input = Output consistency
- No information loss
- Preserves namespace semantics
- Works with multiple ontologies

**Cons**:
- More verbose tokens for LLM
- Requires LLM to track prefixes

### Option C: Hybrid - Show Both Label and ID

**Approach**: Enhance prompt to show both human-readable labels and technical IDs.

**Changes**:
1. Update prompt template:
   ```jinja
   {% for class_id, class_def in classes.items() %}
   - **{{class_id}}** (label: "{{class_def.labels[0].value if class_def.labels else class_id}}"){% if class_def.comment %}: {{class_def.comment}}{% endif %}
   {% endfor %}
   ```

   Example output:
   ```markdown
   - **fo/Recipe** (label: "Recipe"): A Recipe is a combination...
   ```

2. Update instructions:
   ```markdown
   When referencing classes:
   - Use the full prefixed ID (e.g., "fo/Recipe") in JSON output
   - The label (e.g., "Recipe") is for human understanding only
   ```

**Pros**:
- Clearest for LLM
- Preserves all information
- Explicit about what to use

**Cons**:
- Longer prompt
- More complex template

## Recommended Approach

**Option B** (Full Prefixed IDs Consistently) is recommended because:

1. **No Information Loss**: Original URIs preserved correctly
2. **Simpler Logic**: No transformation needed, direct dict lookups work
3. **Namespace Safety**: Handles multiple ontologies without collisions
4. **Semantic Correctness**: Maintains RDF/OWL semantics

## Implementation Plan

### Phase 1: Fix Prompt Examples
- [ ] Update `ontology-prompt.md` example to use prefixed IDs
- [ ] Add namespace prefix explanation section
- [ ] Add guidance for entity instance naming

### Phase 2: Enhance Prompt Template
- [ ] Optionally add labels alongside IDs (Option C enhancement)
- [ ] Document namespace prefixes from ontology metadata
- [ ] Clarify entity instance URI format

### Phase 3: Add Validation Tests
- [ ] Test that LLM outputs match input format
- [ ] Verify URI expansion preserves original URIs
- [ ] Test with multiple ontologies (collision scenarios)

### Phase 4: Improve Error Handling
- [ ] Better logging when URI lookup fails
- [ ] Warn when falling back to constructed URIs
- [ ] Validate LLM output format before parsing

## Test Cases

### Test 1: URI Preservation
```python
# Given ontology class
classes = {"fo/Recipe": {"uri": "http://purl.org/ontology/fo/Recipe", ...}}

# When LLM returns
llm_output = {"subject": "x", "predicate": "rdf:type", "object": "fo/Recipe"}

# Then expanded URI should be
assert expanded == "http://purl.org/ontology/fo/Recipe"
# Not: "https://trustgraph.ai/ontology/food#Recipe"
```

### Test 2: Multi-Ontology Collision
```python
# Given two ontologies
ont1 = {"fo/Recipe": {...}}
ont2 = {"cooking/Recipe": {...}}

# LLM should use full prefix to disambiguate
llm_output = {"object": "fo/Recipe"}  # Not just "Recipe"
```

### Test 3: Entity Instance Format
```python
# Given prompt with food ontology
# LLM should create instances like
{"subject": "recipe:cornish-pasty"}  # Namespace-style
{"subject": "food:beef"}              # Consistent prefix
```

## Open Questions

1. **Should entity instances use namespace prefixes?**
   - Current: `"recipe:cornish-pasty"` (arbitrary)
   - Alternative: Use ontology prefix `"fo:cornish-pasty"`?
   - Alternative: No prefix, expand in URI `"cornish-pasty"` → full URI?

2. **How to handle domain/range in prompt?**
   - Currently shows: `(Recipe → Food)`
   - Should it be: `(fo/Recipe → fo/Food)`?

3. **Should we validate domain/range constraints?**
   - TODO comment at extract.py:470
   - Would catch more errors but more complex

4. **What about inverse properties and equivalences?**
   - Ontology has `owl:inverseOf`, `owl:equivalentClass`
   - Not currently used in extraction
   - Should they be?

## Success Metrics

- ✅ Zero URI information loss (100% preservation of original URIs)
- ✅ LLM output format matches input format
- ✅ No ambiguous examples in prompt
- ✅ Tests pass with multiple ontologies
- ✅ Improved extraction quality (measured by valid triple %)

## Alternative Approach: Simplified Extraction Format

### Philosophy

Instead of asking the LLM to understand RDF/OWL semantics, ask it to do what it's good at: **find entities and relationships in text**.

Let the code handle URI construction, RDF conversion, and semantic web formalities.

### Example: Entity Classification

**Input Text:**
```
Cornish pasty is a traditional British pastry filled with meat and vegetables.
```

**Ontology Schema (shown to LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food
```

**What LLM Returns (Simple JSON):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    }
  ]
}
```

**What Code Produces (RDF Triples):**
```python
# 1. Normalize entity name + type to ID (type prevents collisions)
entity_id = "recipe-cornish-pasty"  # normalize("Cornish pasty", "Recipe")
entity_uri = "https://trustgraph.ai/food/recipe-cornish-pasty"

# Note: Same name, different type = different URI
# "Cornish pasty" (Recipe) → recipe-cornish-pasty
# "Cornish pasty" (Food) → food-cornish-pasty

# 2. Generate triples
triples = [
    # Type triple
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),
    # Label triple (automatic)
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
        o=Value(value="Cornish pasty", is_uri=False)
    )
]
```

### Benefits

1. **LLM doesn't need to:**
   - Understand URI syntax
   - Invent identifier prefixes (`recipe:`, `ingredient:`)
   - Know about `rdf:type` or `rdfs:label`
   - Construct semantic web identifiers

2. **LLM just needs to:**
   - Find entities in text
   - Map them to ontology classes
   - Extract relationships and attributes

3. **Code handles:**
   - URI normalization and construction
   - RDF triple generation
   - Automatic label assignment
   - Namespace management

### Why This Works Better

- **Simpler prompt** = less confusion = fewer errors
- **Consistent IDs** = code controls normalization rules
- **Auto-generated labels** = no missing rdfs:label triples
- **LLM focuses on extraction** = what it's actually good at

### Example: Entity Relationships

**Input Text:**
```
Cornish pasty is a traditional British pastry filled with beef and potatoes.
```

**Ontology Schema (shown to LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food

## Relationships:
- has_ingredient: Relates a recipe to an ingredient it uses (Recipe → Ingredient)
- food: Relates an ingredient to the food that is required (Ingredient → Food)
```

**What LLM Returns (Simple JSON):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ]
}
```

**What Code Produces (RDF Triples):**
```python
# Normalize entity names to URIs
cornish_pasty_uri = "https://trustgraph.ai/food/cornish-pasty"
beef_uri = "https://trustgraph.ai/food/beef"
potatoes_uri = "https://trustgraph.ai/food/potatoes"

# Look up relation URI from ontology
has_ingredient_uri = "http://purl.org/ontology/fo/ingredients"  # from fo/has_ingredient

triples = [
    # Entity type triples (as before)
    Triple(s=cornish_pasty_uri, p=rdf_type, o="http://purl.org/ontology/fo/Recipe"),
    Triple(s=cornish_pasty_uri, p=rdfs_label, o="Cornish pasty"),

    Triple(s=beef_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=beef_uri, p=rdfs_label, o="beef"),

    Triple(s=potatoes_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=potatoes_uri, p=rdfs_label, o="potatoes"),

    # Relationship triples
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=beef_uri, is_uri=True)
    ),
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=potatoes_uri, is_uri=True)
    )
]
```

**Key Points:**
- LLM returns natural language entity names: `"Cornish pasty"`, `"beef"`, `"potatoes"`
- LLM includes types to disambiguate: `subject-type`, `object-type`
- LLM uses relation name from schema: `"has_ingredient"`
- Code derives consistent IDs using (name, type): `("Cornish pasty", "Recipe")` → `recipe-cornish-pasty`
- Code looks up relation URI from ontology: `fo/has_ingredient` → full URI
- Same (name, type) tuple always gets same URI (deduplication)

### Example: Entity Name Disambiguation

**Problem:** Same name can refer to different entity types.

**Real-world case:**
```
"Cornish pasty" can be:
- A Recipe (instructions for making it)
- A Food (the dish itself)
```

**How It's Handled:**

LLM returns both as separate entities:
```json
{
  "entities": [
    {"entity": "Cornish pasty", "type": "Recipe"},
    {"entity": "Cornish pasty", "type": "Food"}
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "produces",
      "object": "Cornish pasty",
      "object-type": "Food"
    }
  ]
}
```

**Code Resolution:**
```python
# Different types → different URIs
recipe_uri = normalize("Cornish pasty", "Recipe")
# → "https://trustgraph.ai/food/recipe-cornish-pasty"

food_uri = normalize("Cornish pasty", "Food")
# → "https://trustgraph.ai/food/food-cornish-pasty"

# Relationship connects them correctly
triple = Triple(
    s=recipe_uri,  # The Recipe
    p="http://purl.org/ontology/fo/produces",
    o=food_uri     # The Food
)
```

**Why This Works:**
- Type is included in ALL references (entities, relationships, attributes)
- Code uses `(name, type)` tuple as lookup key
- No ambiguity, no collisions

### Example: Entity Attributes

**Input Text:**
```
This Cornish pasty recipe serves 4-6 people and takes 45 minutes to prepare.
```

**Ontology Schema (shown to LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method

## Attributes:
- serves: Indicates what the recipe is intended to serve (Recipe → text)
- preparation_time: Time needed to prepare the recipe (Recipe → text)
```

**What LLM Returns (Simple JSON):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty recipe",
      "type": "Recipe"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4-6 people"
    },
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "preparation_time",
      "value": "45 minutes"
    }
  ]
}
```

**What Code Produces (RDF Triples):**
```python
# Normalize entity name to URI
recipe_uri = "https://trustgraph.ai/food/cornish-pasty-recipe"

# Look up attribute URIs from ontology
serves_uri = "http://purl.org/ontology/fo/serves"  # from fo/serves
prep_time_uri = "http://purl.org/ontology/fo/preparation_time"  # from fo/preparation_time

triples = [
    # Entity type triple
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdf_type, is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),

    # Label triple (automatic)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdfs_label, is_uri=True),
        o=Value(value="Cornish pasty recipe", is_uri=False)
    ),

    # Attribute triples (objects are literals, not URIs)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=serves_uri, is_uri=True),
        o=Value(value="4-6 people", is_uri=False)  # Literal value!
    ),
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=prep_time_uri, is_uri=True),
        o=Value(value="45 minutes", is_uri=False)  # Literal value!
    )
]
```

**Key Points:**
- LLM extracts literal values: `"4-6 people"`, `"45 minutes"`
- LLM includes entity type for disambiguation: `entity-type`
- LLM uses attribute name from schema: `"serves"`, `"preparation_time"`
- Code looks up attribute URI from ontology datatype properties
- **Object is literal** (`is_uri=False`), not a URI reference
- Values stay as natural text, no normalization needed

**Difference from Relationships:**
- Relationships: both subject and object are entities (URIs)
- Attributes: subject is entity (URI), object is literal value (string/number)

### Complete Example: Entities + Relationships + Attributes

**Input Text:**
```
Cornish pasty is a savory pastry filled with beef and potatoes.
This recipe serves 4 people.
```

**What LLM Returns:**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4 people"
    }
  ]
}
```

**Result:** 11 RDF triples generated:
- 3 entity type triples (rdf:type)
- 3 entity label triples (rdfs:label) - automatic
- 2 relationship triples (has_ingredient)
- 1 attribute triple (serves)

All from simple, natural language extractions by the LLM!

## References

- Current implementation: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`
- Prompt template: `ontology-prompt.md`
- Test cases: `tests/unit/test_extract/test_ontology/`
- Example ontology: `e2e/test-data/food.ontology`
