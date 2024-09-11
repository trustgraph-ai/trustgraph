
def to_relationships(text):

    prompt = f"""You are a helpful assistant that performs information extraction tasks for a provided text.

Read the provided text. You will model the text as an information network for a RDF knowledge graph in JSON.

Information Network Rules:
- An information network has subjects connected by predicates to objects.
- A subject is a named-entity or a conceptual topic.
- One subject can have many predicates and objects.
- An object is a property or attribute of a subject.
- A subject can be connected by a predicate to another subject.

Reading Instructions:
- Ignore document formatting in the provided text.
- Study the provided text carefully.

Here is the text: 
{text}

Response Instructions:
- Obey the information network rules. 
- Do not return special characters.
- Respond only with well-formed JSON.
- The JSON response shall be an array of JSON objects with keys "subject", "predicate", "object", and "object-entity".
- The JSON response shall use the following structure:

```json
[{{"subject": string, "predicate": string, "object": string, "object-entity": boolean}}]
```

- The key "object-entity" is TRUE only if the "object" is a subject.
- Do not write any additional text or explanations.
"""
    
    return prompt

def to_topics(text):

    prompt = f"""You are a helpful assistant that performs information extraction tasks for a provided text.\nRead the provided text. You will identify topics and their definitions in JSON.

Reading Instructions:
- Ignore document formatting in the provided text.
- Study the provided text carefully.

Here is the text:
{text}

Response Instructions: 
- Do not respond with special characters.
- Return only topics that are concepts and unique to the provided text.
- Respond only with well-formed JSON.
- The JSON response shall be an array of objects with keys "topic" and "definition". 
- The JSON response shall use the following structure:

```json
[{{"topic": string, "definition": string}}]
```

- Do not write any additional text or explanations.
"""
    
    return prompt
    
def to_definitions(text):

    prompt = f"""You are a helpful assistant that performs information extraction tasks for a provided text.\nRead the provided text. You will identify entities and their definitions in JSON.

Reading Instructions:
- Ignore document formatting in the provided text.
- Study the provided text carefully.

Here is the text:
{text}

Response Instructions:
- Do not respond with special characters.
- Return only entities that are named-entities such as: people, organizations, physical objects, locations, animals, products, commodotities, or substances.
- Respond only with well-formed JSON. 
- The JSON response shall be an array of objects with keys "entity" and "definition".
- The JSON response shall use the following structure: 

```json
[{{"entity": string, "definition": string}}]
```

- Do not write any additional text or explanations.
"""
    
    return prompt

def to_rows(schema, text):

    field_schema = [
        f"- Name: {f.name}\n  Type: {f.type}\n  Definition: {f.description}"
        for f in schema.fields
    ]

    field_schema = "\n".join(field_schema)

    schema = f"""Object name: {schema.name}
Description: {schema.description}

Fields:
{field_schema}"""

    prompt = f"""<instructions>
Study the following text and derive objects which match the schema provided.

You must output an array of JSON objects for each object you discover
which matches the schema.  For each object, output a JSON object whose fields
carry the name field specified in the schema.
</instructions>

<schema>
{schema}
</schema>

<text>
{text}
</text>

<requirements>
You will respond only with raw JSON format data. Do not provide
explanations. Do not add markdown formatting or headers or prefixes.
</requirements>"""
    
    return prompt
    
def get_cypher(kg):

    sg2 = []

    for f in kg:

        print(f)

        sg2.append(f"({f.s})-[{f.p}]->({f.o})")

    print(sg2)

    kg = "\n".join(sg2)
    kg = kg.replace("\\", "-")

    return kg

def to_kg_query(query, kg):

    cypher =  get_cypher(kg)

    prompt=f"""Study the following set of knowledge statements. The statements are written in Cypher format that has been extracted from a knowledge graph. Use only the provided set of knowledge statements in your response. Do not speculate if the answer is not found in the provided set of knowledge statements.

Here's the knowledge statements:
{cypher}

Use only the provided knowledge statements to respond to the following:
{query}
"""

    return prompt

def to_document_query(query, documents):

    documents = "\n\n".join(documents)

    prompt=f"""Study the following context. Use only the information provided in the context in your response. Do not speculate if the answer is not found in the provided set of knowledge statements.

Here is the context:
{documents}

Use only the provided knowledge statements to respond to the following:
{query}
"""

    return prompt
