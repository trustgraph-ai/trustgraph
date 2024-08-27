
def to_relationships(template, text):
    return template.format(text=text)
    
def to_definitions(template, text):
    return template.format(text=text)

def to_rows(template, schema, text):

    field_schema = [
        f"- Name: {f.name}\n  Type: {f.type}\n  Definition: {f.description}"
        for f in schema.fields
    ]

    field_schema = "\n".join(field_schema)

    return template.format(schema=schema, text=text)

    schema = f"""Object name: {schema.name}
Description: {schema.description}

Fields:
{schema}"""

    prompt = f""""""
    
    return prompt
    
def get_cypher(kg):
    sg2 = []
    for f in kg:
        sg2.append(f"({f.s})-[{f.p}]->({f.o})")
    kg = "\n".join(sg2)
    kg = kg.replace("\\", "-")
    return kg

def to_kg_query(template, query, kg):
    cypher =  get_cypher(kg)
    return template.format(query=query, graph=cypher)

def to_document_query(template, query, docs):
    docs = "\n\n".join(docs)
    return template.format(query=query, documents=docs)

