{
   "azure": import "components/azure.jsonnet",
   "azure-openai": import "components/azure-openai.jsonnet",
   "bedrock": import "components/bedrock.jsonnet",
   "claude": import "components/claude.jsonnet",
   "cohere": import "components/cohere.jsonnet",
   "document-rag": import "components/document-rag.jsonnet",
   "embeddings-hf": import "components/embeddings-hf.jsonnet",
   "embeddings-ollama": import "components/embeddings-ollama.jsonnet",
   "googleaistudio": import "components/googleaistudio.jsonnet",
   "grafana": import "components/grafana.jsonnet",
   "graph-rag": import "components/graph-rag.jsonnet",
   "triple-store-cassandra": import "components/cassandra.jsonnet",
   "triple-store-neo4j": import "components/neo4j.jsonnet",
   "llamafile": import "components/llamafile.jsonnet",
   "ollama": import "components/ollama.jsonnet",
   "openai": import "components/openai.jsonnet",
   "override-recursive-chunker": import "components/chunker-recursive.jsonnet",

   "prompt-template": import "components/prompt-template.jsonnet",
   "prompt-overrides": import "components/prompt-overrides.jsonnet",

   "pulsar": import "components/pulsar.jsonnet",
   "pulsar-manager": import "components/pulsar-manager.jsonnet",
   "trustgraph-base": import "components/trustgraph.jsonnet",
   "vector-store-milvus": import "components/milvus.jsonnet",
   "vector-store-qdrant": import "components/qdrant.jsonnet",
   "vector-store-pinecone": import "components/pinecone.jsonnet",
   "vertexai": import "components/vertexai.jsonnet",
   "null": {},

   "agent-manager-react": import "components/agent-manager-react.jsonnet",

   // FIXME: Dupes
   "cassandra": import "components/cassandra.jsonnet",
   "neo4j": import "components/neo4j.jsonnet",
   "qdrant": import "components/qdrant.jsonnet",
   "pinecone": import "components/pinecone.jsonnet",
   "milvus": import "components/milvus.jsonnet",
   "trustgraph": import "components/trustgraph.jsonnet",

}
