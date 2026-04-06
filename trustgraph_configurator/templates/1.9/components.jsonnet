{

   // Essentials
   "trustgraph-base": import "core/trustgraph.jsonnet",
   "rev-gateway": import "core/rev-gateway.jsonnet",
   "pulsar": import "pulsar/pulsar.jsonnet",

   // LLMs
   "azure": import "llm/azure.jsonnet",
   "azure-openai": import "llm/azure-openai.jsonnet",
   "bedrock": import "llm/bedrock.jsonnet",
   "claude": import "llm/claude.jsonnet",
   "cohere": import "llm/cohere.jsonnet",
   "googleaistudio": import "llm/googleaistudio.jsonnet",
   "llamafile": import "llm/llamafile.jsonnet",
   "lmstudio": import "llm/lmstudio.jsonnet",
   "mistral": import "llm/mistral.jsonnet",
   "ollama": import "llm/ollama.jsonnet",
   "openai": import "llm/openai.jsonnet",
   "vertexai": import "llm/vertexai.jsonnet",
   "tgi": import "llm/tgi.jsonnet",
   "vllm": import "llm/vllm.jsonnet",

   // Embeddings
   "embeddings-ollama": import "embeddings/embeddings-ollama.jsonnet",
   "embeddings-hf": import "embeddings/embeddings-hf.jsonnet",
   "embeddings-fastembed": import "embeddings/embeddings-fastembed.jsonnet",

   // OCR options
   "ocr": import "ocr/ocr.jsonnet",
   "mistral-ocr": import "ocr/mistral-ocr.jsonnet",

   // Vector stores
   "vector-store-milvus": import "vector-store/milvus.jsonnet",
   "vector-store-qdrant": import "vector-store/qdrant.jsonnet",
   "vector-store-pinecone": import "vector-store/pinecone.jsonnet",

   // Triples stores
   "triple-store-cassandra": import "triple-store/cassandra.jsonnet",
   "triple-store-neo4j": import "triple-store/neo4j.jsonnet",
   "triple-store-falkordb": import "triple-store/falkordb.jsonnet",
   "triple-store-memgraph": import "triple-store/memgraph.jsonnet",

   // Object stores
   "row-store-cassandra": import "row-store/cassandra.jsonnet",

   // Observability support
   "grafana": import "monitoring/grafana.jsonnet",
   "loki": import "monitoring/loki.jsonnet",

   // Pulsar manager is a UI for Pulsar.  Uses a LOT of memory
   "pulsar-manager": import "pulsar/pulsar-manager.jsonnet",

   "override-recursive-chunker": import "core/chunker-recursive.jsonnet",

   // The prompt manager
   "prompt-overrides": import "core/prompt-overrides.jsonnet",

   // Extra MCP services
   "ddg-mcp-server": import "mcp/ddg-mcp-server.jsonnet",

   // Does nothing.  But, can be a hack to overwrite parameters
   "null": {},

   // Passthrough: returns parameters directly, preserving +: merge syntax
   // Also supports JSON-safe routing with prefixed parameters like "cassandra-heap"
   "override": {
       local route = function(target)
           function(prefix, k, v)
               local suffix = std.substr(k, std.length(prefix), std.length(k) - std.length(prefix));
               { [target] +: { [suffix]:: v } },

       local routes = {
           "cassandra-": route("cassandra"),
           "pulsar-": route("pulsar"),
           "qdrant-": route("qdrant"),
           "api-gateway-": route("api-gateway"),
           "librarian-": route("librarian"),
       },

       with_params:: function(pars)
           std.foldl(
               function(acc, k)
                   local matchingPrefixes = [p for p in std.objectFields(routes) if std.startsWith(k, p)];
                   if std.length(matchingPrefixes) > 0 then
                       local prefix = matchingPrefixes[0];
                       acc + routes[prefix](prefix, k, pars[k])
                   else
                       acc + { [k]:: pars[k] },
               std.objectFields(pars),
               {}
           ),
   },

   // Memory profiles
   "memory-profile-low": import "profiles/memory-profile-low.jsonnet",

   // Model hosting

   "hosting-intel-battlemage-vllm":
       import "model-hosting/intel-battlemage-vllm.jsonnet",

   "hosting-cpu-tgi":
       import "model-hosting/cpu-tgi.jsonnet",

   "hosting-intel-xpu-tgi":
       import "model-hosting/intel-xpu-tgi.jsonnet",

   "hosting-intel-gaudi-tgi":
       import "model-hosting/intel-gaudi-tgi.jsonnet",

   "hosting-intel-xpu-vllm":
       import "model-hosting/intel-xpu-vllm.jsonnet",

   "hosting-intel-gaudi-vllm":
       import "model-hosting/intel-gaudi-vllm.jsonnet",

   "hosting-nvidia-gpu-vllm":
       import "model-hosting/nvidia-gpu-vllm.jsonnet",

}
