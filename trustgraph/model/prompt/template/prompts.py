
def to_relationships(template, text):
    return template.format(text=text)
    
def to_definitions(template, text):
    return template.format(text=text)

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

