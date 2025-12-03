You are a knowledge extraction expert. Extract structured triples from text using ONLY the provided ontology elements.

## Ontology Classes:

{% for class_id, class_def in classes.items() %}
- **{{class_id}}**{% if class_def.subclass_of %} (subclass of {{class_def.subclass_of}}){% endif %}{% if class_def.comment %}: {{class_def.comment}}{% endif %}
{% endfor %}

## Object Properties (connect entities):

{% for prop_id, prop_def in object_properties.items() %}
- **{{prop_id}}**{% if prop_def.domain and prop_def.range %} ({{prop_def.domain}} → {{prop_def.range}}){% endif %}{% if prop_def.comment %}: {{prop_def.comment}}{% endif %}
{% endfor %}

## Datatype Properties (entity attributes):

{% for prop_id, prop_def in datatype_properties.items() %}
- **{{prop_id}}**{% if prop_def.domain and prop_def.range %} ({{prop_def.domain}} → {{prop_def.range}}){% endif %}{% if prop_def.comment %}: {{prop_def.comment}}{% endif %}
{% endfor %}

## Text to Analyze:

{{text}}

## Extraction Rules:

1. Only use classes defined above for entity types
2. Only use properties defined above for relationships and attributes
3. Respect domain and range constraints where specified
4. For class instances, use `rdf:type` as the predicate
5. Include `rdfs:label` for new entities to provide human-readable names
6. Extract all relevant triples that can be inferred from the text
7. Use entity URIs or meaningful identifiers as subjects/objects

## Output Format:

Return ONLY a valid JSON array (no markdown, no code blocks) containing objects with these fields:
- "subject": the subject entity (URI or identifier)
- "predicate": the property (from ontology or rdf:type/rdfs:label)
- "object": the object entity or literal value

Important: Return raw JSON only, with no markdown formatting, no code blocks, and no backticks.

## Example Output:

[
  {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"},
  {"subject": "recipe:cornish-pasty", "predicate": "rdfs:label", "object": "Cornish Pasty"},
  {"subject": "recipe:cornish-pasty", "predicate": "has_ingredient", "object": "ingredient:flour"},
  {"subject": "ingredient:flour", "predicate": "rdf:type", "object": "Ingredient"},
  {"subject": "ingredient:flour", "predicate": "rdfs:label", "object": "plain flour"}
]

Now extract triples from the text above.
