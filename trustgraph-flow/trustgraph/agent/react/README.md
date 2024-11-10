
agent-manager-react \
    -p pulsar://localhost:6650 \
    --tool-type \
        shuttle=knowledge-base:query \
        cats=knowledge-base:query \
        compute=text-completion:computation \
    --tool-description \
        shuttle="Query a knowledge base with information about the space shuttle.  The query should be a simple natural language question" \
        cats="Query a knowledge base with information about Mark's cats.  The query should be a simple natural language question" \
        compute="A computation engine which can answer questions about maths and computation" \
    --tool-argument \
        cats="query:string:The search query string" \
        shuttle="query:string:The search query string" \
        compute="computation:string:The computation to solve"

