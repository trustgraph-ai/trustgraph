
def turtle_extract(text):

    prompt = f"""<instructions>
Study the following text and extract knowledge as
information in Turtle RDF format.
When declaring any new URIs, use <https://trustgraph.ai/e#> prefix,
and declare appropriate namespace tags.
</instructions>
    
<text>
{text}
</text>
    
<requirements>
Do not use placeholders for information you do not know.
You will respond only with raw Turtle RDF data. Do not provide
explanations. Do not use special characters in the abstract text. The
abstract must be written as plain text.  Do not add markdown formatting.
</requirements>"""

    return prompt

def scholar(text):

    # Build the prompt for Article style extraction
    jsonexample = """{
    "title": "Article title here",
    "abstract": "Abstract text here",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "people": ["person1", "person2", "person3"]
}"""
    
    promptscholar = f"""Your task is to read the provided text and write a scholarly abstract to fully explain all of the concepts described in the provided text. The abstract must include all conceptual details.
<text>
{text}
</text>
<instructions>

- Structure: For the provided text, write a title, abstract, keywords,
  and people for the concepts found in the provided text. Ignore
  document formatting in the provided text such as table of contents,
  headers, footers, section metadata, and URLs.
- Focus on Concepts The abstract must focus on concepts found in the
  provided text. The abstract must be factually accurate. Do not
  write any concepts not found in the provided text. Do not
  speculate. Do not omit any conceptual details.
- Completeness: The abstract must capture all topics the reader will
  need to understand the concepts found in the provided text. Describe
  all terms, definitions, entities, people, events, concepts,
  conceptual relationships, and any other topics necessary for the
  reader to understand the concepts of the provided text.

- Format: Respond in the form of a valid JSON object.
</instructions>
<example>
{jsonexample}
</example>
<requirements>
You will respond only with the JSON object. Do not provide
explanations. Do not use special characters in the abstract text. The
abstract must be written as plain text.
</requirements>"""

    return promptscholar

def to_json_ld(text):

    prompt = f"""<instructions>
Study the following text and output any facts you discover in
well-structured JSON-LD format.
Use any schema you understand from schema.org to describe the facts.
</instructions>

<text>
{text}
</text>

<requirements>
You will respond only with raw JSON-LD data in JSON format. Do not provide
explanations. Do not use special characters in the abstract text. The
abstract must be written as plain text.  Do not add markdown formatting
or headers or prefixes.  Do not use information which is not present in
the input text.
</requirements>"""
    
    return prompt
    

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
    
