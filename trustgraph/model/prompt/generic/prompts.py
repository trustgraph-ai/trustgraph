
def to_relationships(text):

    prompt = f"""You are a helpful assistant that performs information extraction tasks for a provided text.

Read the provided text. You will model the text as an information network for a RDF knowledge graph.

Information network rules:
- An information network has subjects connected by predicates to objects.
- A subject can have many predicates and objects.
- A subject can be connected by a predicate to another subject.
- Objects shall be either nouns or adjectives.

Here is the provided text: 
{text}

Instructions:
- Obey the information network rules.
- Ignore document formatting. 
- Do not provide explanations or any additional text. 
- Do not use special characters.
- The key "object-entity" is true if it is a Named-Entity.
- Respond only with a well-formed JSON using the following example:

JSON example: [{{"subject": string, "predicate": string, "object": string, "object-entity": boolean}}]
"""
    
    return prompt

def to_topics(text):

    prompt = f"""You are a helpful assistant that performs information extraction tasks for a provided text.\nRead the provided text. You will identify topics and their definitions.

Here is the provided text: 
{text}

Instructions:
- Ignore document formatting. 
- Do not provide explanations or any additional text. 
- Do not use special characters.
- Identify only topics that are unique to the provided text.
- Respond only with a well-formed JSON using the following example:

JSON example: [{{"topic": string, "definition": string}}]
"""
    
    return prompt
    
def to_definitions(text):

    prompt = f"""You are a helpful assistant that performs information extraction tasks for a provided text.\nRead the provided text. You will identify named-entities and their definitions.

Here is the provided text: 
{text}

Instructions:
- Ignore document formatting. 
- Do not provide explanations or any additional text. 
- Do not use special characters.
- Identity only entities that are named-entities.
- Respond only with a well-formed JSON using the following example:

JSON example: [{{"entity": string, "definition": string}}]"""
    
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
