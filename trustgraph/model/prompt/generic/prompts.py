
def to_relationships(text):

    prompt = f"""<instructions>
Study the following text and derive entity relationships.  For each
relationship, derive the subject, predicate and object of the relationship.
Output relationships in JSON format as an arary of objects with fields:
- subject: the subject of the relationship
- predicate: the predicate
- object: the object of the relationship
- object-entity: false if the object is a simple data type: name, value or date.  true if it is an entity.
</instructions>

<text>
{text}
</text>

<requirements>
You will respond only with raw JSON format data. Do not provide
explanations. Do not use special characters in the abstract text. The
abstract must be written as plain text.  Do not add markdown formatting
or headers or prefixes.
</requirements>"""
    
    return prompt
    
def to_definitions(text):

    prompt = f"""<instructions>
Study the following text and derive definitions for any discovered entities.
Do not provide definitions for entities whose definitions are incomplete
or unknown.
Output relationships in JSON format as an arary of objects with fields:
- entity: the name of the entity
- definition: English text which defines the entity
</instructions>

<text>
{text}
</text>

<requirements>
You will respond only with raw JSON format data. Do not provide
explanations. Do not use special characters in the abstract text. The
abstract will be written as plain text.  Do not add markdown formatting
or headers or prefixes.  Do not include null or unknown definitions.
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
