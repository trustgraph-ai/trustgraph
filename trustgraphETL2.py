
import json
import re
import rdflib
import time
from langchain_community.document_loaders import PyPDFLoader
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from langchain_community.llms import Ollama

llm = Ollama(
    base_url="http://monster:11434",
#     model="deepseek-v2"
     model="phi3:14b"
#     model="gemma2"
)

exampleXML = f"""## RDF/XML Examples:

```xml
<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:ex="http://example.org/stuff/1.0/">

  <rdf:Description rdf:about="http://www.w3.org/TR/rdf-syntax-grammar"
             dc:title="RDF1.1 XML Syntax">
    <ex:editor>
      <rdf:Description ex:fullName="Dave Beckett">
        <ex:homePage rdf:resource="http://purl.org/net/dajobe/" />
      </rdf:Description>
    </ex:editor>
  </rdf:Description>
</rdf:RDF>
```

```xml
<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:dc="http://purl.org/dc/elements/1.1/">

  <rdf:Description rdf:about="http://www.w3.org/TR/rdf-syntax-grammar">
    <dc:title>RDF 1.1 XML Syntax</dc:title>
    <dc:title xml:lang="en">RDF 1.1 XML Syntax</dc:title>
    <dc:title xml:lang="en-US">RDF 1.1 XML Syntax</dc:title>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/buecher/baum" xml:lang="de">
    <dc:title>Der Baum</dc:title>
    <dc:description>Das Buch ist außergewöhnlich</dc:description>
    <dc:title xml:lang="en">The Tree</dc:title>
  </rdf:Description>
</rdf:RDF>
```

```xml
<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:ex="http://example.org/stuff/1.0/">

  <rdf:Description rdf:about="http://example.org/item01"> 
    <ex:prop rdf:parseType="Literal" xmlns:a="http://example.org/a#">
      <a:Box required="true">
        <a:widget size="10" />
        <a:grommit id="23" />
      </a:Box>
    </ex:prop>
  </rdf:Description>
</rdf:RDF>
```

## RDF/XML Instructions:
1. All valid RDF/XML shall written with the following first line: <?xml version="1.0"?>
2. The subject of a RDF triple must be a URI, Uniform Resource Identifier.
3. The predicate of a RDF triple must be a URI, Uniform Resource Identier.
4. All URIs must use the following base URL: http://example.org/
5. Predicates should be written using knowledge schema using the SKOS, Simple Knowledge Organization System, approach.
6. The object of a RDF triple can be a URI or a value. 
7. If the object of a RDF triple is a value, the object should have a XSD type.
"""

exampleTurtle = """Knowledge is written between <<<>>>>. That knowledge will be rewritten as RDF Turtle.

<<<Fred lives with Hope. Fred is a cat. Fred has 4 legs.>>>

Here's the RDF Turtle for the knowledge
```turtle
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix animal: <http://example.org/animal/> .
@prefix prop: <http://example.org/property/> .
@prefix type: <http://example.org/type/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

animal:fred
    prop:has-legs 4 ;
    prop:lives-with animal:hope ;
    a type:cat ;
    rdfs:label "Fred" .

animal:hope
    prop:has-legs 4 ;
    prop:lives-with animal:fred ;
    a type:cat ;
    rdfs:label "Hope" .

prop:has-legs
    a rdfs:Property ;
    rdfs:label "has legs" .

prop:lives-with
    a rdfs:Property ;
    rdfs:label "lives with" .

type:cat
    a rdfs:Class ;
    rdfs:label "cat" .
```

# RDF Turtle Rules
1. The object of a RDF triple can be a URI or a value. 
2. If the object of a RDF triple is a value, the object should have a XSD type.
3. All triples must have a subject, predicate, and object.
4. A subject shall always be followed by a predicate and object.
5. When a subject has multiple sets of predicates and objects, use a semicolon character to separate each set of predicates and objects.
6. When a subject and predicate have multiple objects, use a comma character to separate the set of objects.
7. Use the 'a' character in place of the predicate 'is'.
8. Use @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
9. Use @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
10. Use @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
"""

# Build the prompt for Article style extraction
jsonexample = """{
    "title": "Article title here",
    "abstract": "Abstract text here",
    "keywords": ["keyword1", "keyword2", "keyword3"],
    "people": ["person1", "person2", "person3"]
}"""

def scholar(chunk):
    promptscholar = f"""Your task is to read the provided text and write a scholarly abstract to fully explain all of the concepts described in the provided text. The abstract should include all conceptual details.
<text>
{chunk}
</text>
<instructions>

- Structure: For the provided text, write a title, abstract, keywords,
  and people for the concepts found in the provided text. Ignore
  document formatting in the provided text such as table of contents,
  headers, footers, section metadata, and URLs.
- Focus on Concepts The abstract should focus on concepts found in the
  provided text. The abstract should be factually accurate. Do not
  write any concepts not found in the provided text. Do not
  speculate. Do not omit any conceptual details.
- Completeness: The abstract should capture all topics the reader will
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
abstract should be written as plain text.
</requirements>"""

    return promptscholar

# Build the prompt for the custom RDF/XML schema
def schema(article):
    promptschema = f"""[INST]You are a scholar. Your subject of expertise is {article['title']}. You have expert understanding of knowledge schemas that are parsed into RDF knowledge graphs. Your task is to read the provided article and write a complete RDF/XML document for the provided article. You will respond only with the RDF/XML document. Do not provide explanations. Obey all RDF/XML instructions.

    # Provided Article:
    {article['abstract']}

    # Example RDF/XML and Instructions:
    {exampleXML}
    [/INST]

    # Keyword Annotations:
    Add RDF/XML labels to the applicable concepts using the following list of keywords:
    {article['keywords']}

    # People Annotations:

    Add RDF/XML labels to the applicable concepts using the following list of people:
    {article['people']}
    """
    return promptschema

# Build the prompt for the SKOS style RDF/XML schema
def skos(article):
    promptconcepts = f"""[INST]You are a scholar. Your subject of expertise is {article['title']}. You have expert understanding of knowledge schemas that are parsed into RDF knowledge graphs. Your task is to read the provided article and write a complete RDF/XML document for the provided article that uses SKOS, Simple Knowledge Organization System, to structure the conceptual relationships in the article. You will respond only with the RDF/XML document. Do not provide explanations. Obey all RDF/XML instructions.

    # Provided Article:
    {article['abstract']}

    # RDF/XML Example and Instructions:
    {exampleXML}

    # Keyword Annotations:
    Add RDF/XML labels to the applicable concepts using the following list of keywords:
    {article['keywords']}

    # People Annotations:
    Add RDF/XML labels to the applicable concepts using the following list of people:
    {article['people']}
    [/INST]
    """
    return promptconcepts

# Add the outputs from the first pass to stabilize the build process
def example_follow(x1, x2):
    exampleXML = f"""## RDF/XML Examples:

```xml
<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:dc="http://purl.org/dc/elements/1.1/"
            xmlns:ex="http://example.org/stuff/1.0/">

  <rdf:Description rdf:about="http://www.w3.org/TR/rdf-syntax-grammar"
             dc:title="RDF1.1 XML Syntax">
    <ex:editor>
      <rdf:Description ex:fullName="Dave Beckett">
        <ex:homePage rdf:resource="http://purl.org/net/dajobe/" />
      </rdf:Description>
    </ex:editor>
  </rdf:Description>
</rdf:RDF>
```

```xml
<?xml version="1.0" encoding="utf-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:dc="http://purl.org/dc/elements/1.1/">

  <rdf:Description rdf:about="http://www.w3.org/TR/rdf-syntax-grammar">
    <dc:title>RDF 1.1 XML Syntax</dc:title>
    <dc:title xml:lang="en">RDF 1.1 XML Syntax</dc:title>
    <dc:title xml:lang="en-US">RDF 1.1 XML Syntax</dc:title>
  </rdf:Description>

  <rdf:Description rdf:about="http://example.org/buecher/baum" xml:lang="de">
    <dc:title>Der Baum</dc:title>
    <dc:description>Das Buch ist außergewöhnlich</dc:description>
    <dc:title xml:lang="en">The Tree</dc:title>
  </rdf:Description>
</rdf:RDF>
```

```xml
<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            xmlns:ex="http://example.org/stuff/1.0/">

  <rdf:Description rdf:about="http://example.org/item01"> 
    <ex:prop rdf:parseType="Literal" xmlns:a="http://example.org/a#">
      <a:Box required="true">
        <a:widget size="10" />
        <a:grommit id="23" />
      </a:Box>
    </ex:prop>
  </rdf:Description>
</rdf:RDF>
```

```xml
{x1}
```

```xml
{x2}
```

## RDF/XML Instructions:
1. All valid RDF/XML shall written with the following first line: <?xml version="1.0"?>
2. The subject of a RDF triple must be a URI, Uniform Resource Identifier.
3. The predicate of a RDF triple must be a URI, Uniform Resource Identier.
4. All URIs must use the following base URL: http://example.org/
5. Predicates should be written using knowledge schema using the SKOS, Simple Knowledge Organization System, approach.
6. The object of a RDF triple can be a URI or a value. 
7. If the object of a RDF triple is a value, the object should have a XSD type.
"""
    return exampleXML

# Build the follow prompt for the custom RDF/XML schema
def schema_follow(article, example_follow):
    promptschema = f"""[INST]You are a scholar. Your subject of expertise is {article['title']}. You have expert understanding of knowledge schemas that are parsed into RDF knowledge graphs. Your task is to read the provided article and write a complete RDF/XML document for the provided article. You will respond only with the RDF/XML document. Do not provide explanations. Obey all RDF/XML instructions.

    # Provided Article:
    {article['abstract']}

    # Example RDF/XML and Instructions:
    {example_follow}

    # Keyword Annotations:
    Add RDF/XML labels to the applicable concepts using the following list of keywords:
    {article['keywords']}

    # People Annotations:
    Add RDF/XML labels to the applicable concepts using the following list of people:
    {article['people']}
    [/INST]
    """
    return promptschema

# Build the follow prompt for the SKOS style RDF/XML schema
def skos_follow(article, example_follow):
    promptconcepts = f"""[INST]You are a scholar. Your subject of expertise is {article['title']}. You have expert understanding of knowledge schemas that are parsed into RDF knowledge graphs. Your task is to read the provided article and write a complete RDF/XML document for the provided article that uses SKOS, Simple Knowledge Organization System, to structure the conceptual relationships in the article. You will respond only with the RDF/XML document. Do not provide explanations. Obey all RDF/XML instructions.

    # Provided Article:
    {article['abstract']}

    # RDF/XML Example and Instructions:
    {example_follow}

    # Keyword Annotations:
    Add RDF/XML labels to the applicable concepts using the following list of keywords:
    {article['keywords']}

    # People Annotations:
    Add RDF/XML labels to the applicable concepts using the following list of people:
    {article['people']}
    [/INST]
    """
    return promptconcepts
    

def p1(chunk):
    promptcustom = f"""[INST]You write knowledge schemas that are parsed into RDF knowledge graphs. You read the provided text and develop a knwoledge schema to represent the concepts. Your task is to read the provided text and write a RDF Turtle schema for the concepts found in the provided text. You will respond only with the RDF Turtle schema. Do not provide explanations. Obey all of the provided RDF Turtle rules.

    # RDF Turtle Example and Rules
    {exampleTurtle}

    # Provided Text
    {chunk}
    [/INST]
    """
    return promptcustom

def p2(chunk):
    promptconcepts = f"""[INST]You write knowledge schemas that are parsed into RDF knowledge graphs. You read the provided text and develop a knwoledge schema to represent the conceptual relationships in the text. Your task is to read the provided text and write a RDF Turtle schema for the concepts found in the provided text using SKOS, Simple Knowledge Organization System. You will respond only with the RDF Turtle schema. Do not provide explanations. Obey all of the provided RDF Turtle rules.

    # Valid RDF Turtle Example and Rules
    {exampleTurtle}

    # Provided Text
    {chunk}
    [/INST]
    """
    return promptconcepts

def summaryprompt(chunk):
    promptsummary = f"""[INST]You are an analyst. You read complex text and write a detailed summary. Your task is to read the provided text and write a thorough summary that captures all of the key points.

    # Provided text:
    {chunk}

    # Instructions:
    ## Summarize:
    In clear and concise language, summarize the key points in the provided text.

    ## Key Points:
    It is important to capture unique terms and their definitions, entities, people, events, concepts, conceptual relationships, and relationships between entities and people.

    ## Requirements:
    Include all key points in the summary. Do not omit any facts that might be considered a key point.
    [/INST]
    """
    return promptsummary

def extractpdf(path):
    loader = PyPDFLoader(path)
    pages = loader.load_and_split()
    pdf = f""
    for page in pages:
        content = page.page_content
        pdf += "".join(content)
    return pdf

def chunktext(splitpdf, chunk_size, chunk_overlap):
    node_parser = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = node_parser.get_nodes_from_documents([Document(text=splitpdf)], show_progress=False)
    textlist = []
    for node in nodes:
        textnode = node.text
        textlist.append(textnode)
    return textlist

def OLDcallmixtral(prompt):
    body = json.dumps({
        "prompt": prompt,
        "max_tokens": 4096,
        "temperature": 0.0,
        "top_p": 0.95,
        "top_k": 30
    })

    modelId = 'mistral.mixtral-8x7b-instruct-v0:1'
    accept = 'application/json'
    contentType = 'application/json'
    response = bedrock.invoke_model(body=body, modelId=modelId, accept=accept, contentType=contentType)
    metadata = response['ResponseMetadata']['HTTPHeaders']
    inputtokens = metadata['x-amzn-bedrock-input-token-count']
    outputtokens = metadata['x-amzn-bedrock-output-token-count']
    response_body = json.loads(response.get("body").read())
    outputtext = response_body['outputs'][0]['text']
    output = {
        "text": outputtext,
        "input_tokens": inputtokens,
        "output_tokens": outputtokens
    }
    return output

def callmixtral(prompt):

    resp = llm.invoke(prompt)
    return resp

def count_tokens(metadata):
    inputtokens 


def extract_xml(text):
    cleantext = replace_ampersand(text)
    pattern = r'<\?xml version="1\.0"\?>.*?</rdf:RDF>'
    match = re.search(pattern, cleantext, re.DOTALL)
    
    if match:
        return match.group()
    else:
        return None

def replace_ampersand(text):
    return text.replace('&', 'and')

# Not currently using
def load_json_from_string(json_string):
    # Remove newline characters
    json_string = json_string.replace('\n', '')
    
    # Check if the string contains ```json delimiters
    if "```json" in json_string:
        # Find the start and end indices of the JSON object
        start_index = json_string.find("```json") + 7
        end_index = json_string.rfind("```")

        # Extract the JSON object from the string
        json_object = json_string[start_index:end_index].strip()
    else:
        # Assume the entire string is a valid JSON object
        json_object = json_string

    try:
        # Load the JSON object as a dictionary
        data_dict = json.loads(json_object)
        return data_dict
    except json.JSONDecodeError:
        # Return None if the string is not a valid JSON object
        return None

# Returns JSON for the Scholar Abstract process
def extract_json_from_output(output):
    # Get the text content from the output dictionary
    text_content = output['text']

    # Define the keys we're interested in
    target_keys = ['title', 'abstract', 'keywords', 'people']

    # Initialize an empty dictionary to store our extracted data
    extracted_data = {}

    # Use regex to find JSON-like structures for each key
    for key in target_keys:
        pattern = r'"{0}"\s*:\s*(\[.*?\]|\{{.*?\}}|".*?")'.format(re.escape(key))
        match = re.search(pattern, text_content, re.DOTALL)
        if match:
            # Extract the value and remove any leading/trailing whitespace
            value = match.group(1).strip()
            
            # If the value is a list or dict, parse it
            if value.startswith('[') or value.startswith('{'):
                try:
                    extracted_data[key] = json.loads(value)
                except json.JSONDecodeError:
                    # If parsing fails, store it as a string
                    extracted_data[key] = value
            else:
                # Remove quotes for string values
                extracted_data[key] = value.strip('"')

    return extracted_data

# Not currently using
def convert_summary(dataset):
    num_passes = len(dataset)
    print("Beginning Converting to Summaries")

    start_time = time.time()  # Start the timer

    summaries = []

    for i in range(5):
        print(f"Begin Pass {i+1}")
        promptchunk = dataset[i]
        prompt = summaryprompt(promptchunk)
        output = callmixtral(prompt)
        outputtext = output['text']
        summaries.append(outputtext)
        print(f"Finished Pass {i+1}")

    end_time = time.time()  # End the timer
    total_time = end_time - start_time  # Calculate the total time
    print(f"Total time taken: {total_time:.2f} seconds")
    return summaries

def count_tokens(in_tokens, out_tokens, running_total):
    running_total['input_tokens'] = running_total['input_tokens'] + in_tokens
    running_total['output_tokens'] = running_total['output_tokens'] + out_tokens
    running_count = {'input_tokens': running_total['input_tokens'], 'output_tokens': running_total['output_tokens']}
    return running_count

def extract_articles(dataset):
    num_passes = len(dataset)

    # Initialize the token counts since this is the first step
    in_tokens = 0
    out_tokens = 0
    running_total = {'input_tokens': 0, 'output_tokens': 0}
    running = count_tokens(in_tokens, out_tokens, running_total)
    print("Beginning Converting to Articles")
    print(f"Current Input Tokens: {running['input_tokens']}\nCurrent Output Tokens: {running['output_tokens']}")

    start_time = time.time()  # Start the timer

    articles = []

    i = 0
    while i < num_passes:
        print(f"Begin Pass {i+1}")
        promptchunk = dataset[i]
        prompt = scholar(promptchunk) #Build the prompt
        output = callmixtral(prompt)
        outputjson = extract_json_from_output(output)

        # Check for valid JSON
        if outputjson is None:
            print(f"Failed to parse JSON in Pass {i+1}. Retrying...")
            continue  # Restart the loop for this index
            
        articles.append(outputjson)
        running = count_tokens(int(output['input_tokens']), int(output['output_tokens']), running)
        print(f"Finished Pass {i+1}")
        print(f"Pass {i+1} Input Tokens: {output['input_tokens']}\nPass{i+1} Output Tokens: {output['output_tokens']}")

        i += 1  # Only increment if successful

    end_time = time.time()  # End the timer
    total_time = end_time - start_time  # Calculate the total time

    inputcost = running['input_tokens'] * priceperinput
    outputcost = running['output_tokens'] * priceperoutput
    totalcost = round(inputcost + outputcost,2)
    
    print(f"Total time taken: {total_time:.2f} seconds")
    print(f"Total Input Tokens: {running['input_tokens']}\nTotal Output Tokens: {running['output_tokens']}")
    print(f"Total Cost: ${totalcost}")
    return articles

# NOT CURRENTLY USING
def full_extract(dataset):
    g = rdflib.Graph()
    num_passes = len(dataset)
    print(f"Initializing Graph and beginning extraction:")

    start_time = time.time()  # Start the timer

    for i in range(num_passes):
        print(f"Begin Pass {i+1}")
        output1 = ""
        output2 = ""
        promptchunk = dataset[i]
        prompt1 = p1(promptchunk)
        prompt2 = p2(promptchunk)
        
        output1 = callmixtral(prompt1)
        output1text = output1['text']

        # Extract text between ### characters from output1
        match1 = re.search(r'###(.*?)###', output1text, re.DOTALL)
        if match1:
            data1 = match1.group()
            g.parse(data=data1, format="turtle")
            print(f"Complete first half of Pass {i+1} from ###")
        else:
            g.parse(data=output1text, format="turtle")
            print(f"Complete first half of Pass {i+1} raw")

        output2 = callmixtral(prompt2)
        output2text = output2['text']

        # Extract text between ### characters from output2
        match2 = re.search(r'###(.*?)###', output2text, re.DOTALL)
        if match2:
            data2 = match2.group()
            g.parse(data=data2, format="turtle")
            print(f"Completed Pass {i+1} from ###")
        else:
            g.parse(data=output2text, format="turtle")
            print(f"Complete Pass {i+1} raw")
        
        running_length = len(g)
        print(f"Pass {i+1} Graph Length: {running_length}")

    end_time = time.time()  # End the timer
    total_time = end_time - start_time  # Calculate the total time

    outputpath = f"../Columbia_graph_extract.ttl"
    g.serialize(destination=outputpath)
    print("Holy shit! This actually worked?!?!?!")
    print(f"Total time taken: {total_time:.2f} seconds")
    return

def firstpass_build(dataset):
    firstpass = []
    out1 = ""
    out2 = ""
    chunk = dataset[0]
    p1 = schema(chunk)
    p2 = skos(chunk)
    out1 = callmixtral(p1)
    out1text = out1['text']
    out2 = callmixtral(p2)
    out2text = out2['text']
    xml1 = extract_xml(out1text)
    xml2 = extract_xml(out2text)
    firstpass.append(xml1)
    firstpass.append(xml2)
    return firstpass

# NOT CURRENTLY USING
def build_graph(dataset):
    start_time = time.time()  # Start the timer

    #Build the first set of outputs
    firstset = []
    firstset = firstpass_build(dataset)
    example1 = firstset[0]
    example2 = firstset[1]

    #Build the new set of examples using first pass outputs
    newexamples = example_follow(example1, example2)
    
    print(f"Initializing Graph:")
    g = rdflib.Graph()
    # Parse the outputs from the first pass function
    g.parse(data=firstset[0], format="xml")
    g.parse(data=firstset[1], format="xml")
    print(f"Parsed First Pass, Graph Length: {len(g)}")
    
    num_passes = len(dataset)

    for i in range(1, num_passes, 1):
        output1 = ""
        output2 = ""
        promptchunk = dataset[i]
        prompt1 = schema_follow(promptchunk, newexamples) #Build the schema follow prompt
        prompt2 = skos_follow(promptchunk, newexamples) #Build the SKOS follow prompt
        
        # Get schema style output
        output1 = callmixtral(prompt1)
        output1text = output1['text']

        # Extract text between ```xml``` characters from output1
        match1 = extract_xml(output1text)
        if match1:
            data1 = match1
            g.parse(data=data1, format="xml")

        # Get SKOS style output
        output2 = callmixtral(prompt2)
        output2text = output2['text']

        # Extract text between ```xml``` characters from output2
        match2 = extract_xml(output2text)
        if match2:
            data2 = match2
            g.parse(data=data2, format="xml")
        
        running_length = len(g)
        print(f"Parsed Pass {i+1}, Graph Length: {running_length}")

    end_time = time.time()  # End the timer
    total_time = end_time - start_time  # Calculate the total time

    outputpath = f"../Columbia_graph_extract.ttl"
    g.serialize(destination=outputpath, format="turtle")
    print("Holy shit! This actually worked?!?!?!")
    print(f"Total time taken: {total_time:.2f} seconds")
    return

# Graph Building with some error handling and return the graph
def build_graph_robust(dataset):
    start_time = time.time()  # Start the timer

    #Build the first set of outputs
    firstset = []
    firstset = firstpass_build(dataset)
    example1 = firstset[0]
    example2 = firstset[1]

    #Build the new set of examples using first pass outputs
    newexamples = example_follow(example1, example2)
    
    print(f"Initializing Graph:")
    g = rdflib.Graph()
    # Parse the outputs from the first pass function
    try:
        g.parse(data=firstset[0], format="xml")
        g.parse(data=firstset[1], format="xml")
        print(f"Parsed First Pass, Graph Length: {len(g)}")
    except Exception as e:
        print(f"Error parsing first pass outputs: {str(e)}")
        return
    
    num_passes = len(dataset)

    i = 1
    while i < num_passes:
        output1 = ""
        output2 = ""
        promptchunk = dataset[i]
        prompt1 = schema_follow(promptchunk, newexamples) #Build the schema follow prompt
        prompt2 = skos_follow(promptchunk, newexamples) #Build the SKOS follow prompt
        
        # Get schema style output
        output1 = callmixtral(prompt1)
        output1text = output1['text']

        # Extract text between ```xml``` characters from output1
        match1 = extract_xml(output1text)
        if match1:
            data1 = match1
            try:
                g.parse(data=data1, format="xml")
            except Exception as e:
                print(f"Error parsing schema output in pass {i+1}: {str(e)}\n\nTrying Again...")
                continue

        # Get SKOS style output
        output2 = callmixtral(prompt2)
        output2text = output2['text']

        # Extract text between ```xml``` characters from output2
        match2 = extract_xml(output2text)
        if match2:
            data2 = match2
            try:
                g.parse(data=data2, format="xml")
            except Exception as e:
                print(f"Error parsing SKOS output in pass {i+1}: {str(e)}\n\nTrying Again...")
                continue
        
        running_length = len(g)
        print(f"Parsed Pass {i+1}, Graph Length: {running_length}")
        i += 1

    end_time = time.time()  # End the timer
    total_time = end_time - start_time  # Calculate the total time

    # Don't write graph file for testing
    #outputpath = f"./Columbia_graph_extract.ttl"
    #g.serialize(destination=outputpath, format="turtle")
    print("Holy shit! This actually worked?!?!?!")
    print(f"Total time taken: {total_time:.2f} seconds")
    return g

# Get a list of subjects from graph as URIs
def get_subject_list(graph):
    query = """
    SELECT DISTINCT ?subject
    WHERE {
        ?subject ?predicate ?object .
    }
    """

    subjects = graph.query(query)

    subjectlist = []
    for row in subjects:
        text = f"{row.subject}"
        subjectlist.append(text)

    return subjectlist

# Function for removing URI artifacts to return clean text
def clean_resource(resource):
    # Remove the URL prefixes
    cleaned_resource = resource.replace("http://example.org/", "")
    cleaned_resource = cleaned_resource.replace("http://www.w3.org/2004/02/skos/core#", "")
    cleaned_resource = cleaned_resource.replace("http://www.w3.org/1999/02/22-rdf-syntax-ns#", "")
    cleaned_resource = cleaned_resource.replace("http://www.w3.org/2001/XMLSchema#", "")
    cleaned_resource = cleaned_resource.replace("http://purl.org/dc/elements/1.1/", "")
    
    # Replace special symbols with a space
    cleaned_resource = re.sub(r'[_#/]', ' ', cleaned_resource)
    
    return cleaned_resource

# Clean the entire subject list
def clean_subject_list(subjectlist):
    cleaned_subjects = []
    for subject in subjectlist:
        clean = f"{clean_resource(subject)}"
        cleaned_subjects.append(clean)

    return cleaned_subjects

# Dump all the triples from the Graph
def get_triples_list(graph):
    triples_list = list(graph.triples((None, None, None)))

    semantic_list = []
    for subject, predicate, object in triples_list:
        triple = f"{subject} {predicate} {object}"
        semantic_list.append(triple)

    return semantic_list

#Clean the entire triples list
def clean_triples_list(tripleslist):
    cleaned_triples = []
    for triple in tripleslist:
        cleaned_triple = clean_resource(triple)
        cleaned_triples.append(cleaned_triple)

    return cleaned_triples

# Build UniSim instance for graph subjects
def build_subject_Sim(graph):
    subject_sim = TextSim()
    subject_sim.reset_index() # Make sure it's empty
    subject_sim = TextSim(
        store_data=True, # set to False for large datasets to save memory
        index_type="exact", # set to "approx" for large datasets to use ANN search
        batch_size=128, # increasing batch_size on GPU may be faster
        use_accelerator=True, # uses GPU if available, otherwise uses CPU
    )

    subjects = get_subject_list(graph) # Get the subjects
    clean_subjects = clean_subject_list(subjects) # Clean the subjects
    idx = subject_sim.add(clean_subjects) # Build sim
    return subject_sim

# Build UniSim instance for graph triples
def build_triples_Sim(graph):
    triples_sim = TextSim()
    triples_sim.reset_index() # Make sure it's empty
    triples_sim = TextSim(
        store_data=True, # set to False for large datasets to save memory
        index_type="exact", # set to "approx" for large datasets to use ANN search
        batch_size=128, # increasing batch_size on GPU may be faster
        use_accelerator=True, # uses GPU if available, otherwise uses CPU
    )

    triples = get_triples_list(graph) # Get the triples
    clean_triples = clean_triples_list(triples) # Clean the triples
    idx = triples_sim.add(clean_triples) # Build sim
    return triples_sim
