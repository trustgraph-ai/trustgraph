
prompt-template \
    -p pulsar://localhost:6650 \
    --system-prompt 'You are a {{attitude}}, you are called {{name}}' \
    --global-term \
        'name=Craig' \
        'attitude=LOUD, SHOUTY ANNOYING BOT' \
    --prompt \
        'question={{question}}' \
        'french-question={{question}}' \
        "analyze=Find the name and age in this text, and output a JSON structure containing just the name and age fields: {{description}}.  Don't add markup, just output the raw JSON object." \
        "graph-query=Study the following knowledge graph, and then answer the question.\\n\nGraph:\\n{% for edge in knowledge %}({{edge.0}})-[{{edge.1}}]->({{edge.2}})\\n{%endfor%}\\nQuestion:\\n{{question}}" \
        "extract-definition=Analyse the text provided, and then return a list of terms and definitions.  The output should be a JSON array, each item in the array is an object with fields 'term' and 'definition'.Don't add markup, just output the raw JSON object.  Here is the text:\\n{{text}}" \
    --prompt-response-type \
        'question=text' \
        'analyze=json' \
        'graph-query=text' \
        'extract-definition=json' \
    --prompt-term \
        'question=name:Bonny' \
        'french-question=attitude:French-speaking bot' \
    --prompt-schema \
        'analyze={ "type" : "object", "properties" : { "age": { "type" : "number" }, "name": { "type" : "string" } } }' \
        'extract-definition={ "type": "array", "items": { "type": "object", "properties": { "term": { "type": "string" }, "definition": { "type": "string" } }, "required": [ "term", "definition" ] } }'
    
