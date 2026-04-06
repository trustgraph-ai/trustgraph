// Low memory profile - reduces memory allocation across components.
// Include this at the END of your configuration to override default memory
// settings with lower values suitable for memory-constrained environments.
//
// Usage: {"name": "memory-profile-low", "parameters": {}}
//
// Note: This trades some performance headroom for reduced memory usage.
// Monitor for OOM errors under heavy load.

{

    // Override Pulsar stack memory settings
    "pulsar" +: {

        // Zookeeper: 512M -> 300M
        "zk-memory-limit":: "300M",
        "zk-memory-reservation":: "200M",
        "zk-heap":: "128m",
        "zk-direct-memory":: "64m",

        // Bookie: 1024M -> 600M
        "bookie-memory-limit":: "600M",
        "bookie-memory-reservation":: "400M",
        "bookie-heap":: "128m",
        "bookie-direct-memory":: "128m",

        // Broker: 800M -> 512M
        "broker-memory-limit":: "512M",
        "broker-memory-reservation":: "400M",
        "broker-heap":: "192m",
        "broker-direct-memory":: "192m",

        // Pulsar-init: 256M -> 128M
        "init-memory-limit":: "128M",
        "init-memory-reservation":: "128M",
        "init-heap":: "64m",
        "init-direct-memory":: "64m",

    },

    // Override Cassandra memory settings: 1000M -> 600M
    "cassandra" +: {
        "memory-limit":: "600M",
        "memory-reservation":: "500M",
        "heap":: "200M",
    },

    // Override Qdrant memory settings: 1024M -> 600M
    // Also enables mmap for vectors/payloads (trades latency for memory)
    "qdrant" +: {
        "memory-limit":: "600M",
        "memory-reservation":: "500M",
        "memmap-threshold-kb":: "1",
        "on-disk-payload":: "true",
    },

    // TrustGraph core services - 50% memory reservations
    "api-gateway" +: {
        "memory-reservation":: "256M",  // 512M -> 256M
    },

    "chunker" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "config-svc" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "pdf-decoder" +: {
        "memory-reservation":: "256M",  // 512M -> 256M
    },

    "mcp-tool" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "mcp-server" +: {
        "memory-reservation":: "128M",  // 256M -> 128M
    },

    "metering" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "metering-rag" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "kg-store" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "kg-manager" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "prompt" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "prompt-rag" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "document-rag" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "document-embeddings" +: {
        "memory-reservation":: "256M",  // 512M -> 256M
    },

    "librarian" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "agent-manager" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    // Graph RAG services
    "kg-extract-definitions" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "kg-extract-relationships" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "kg-extract-agent" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "kg-extract-ontology" +: {
        "memory-reservation":: "150M",  // 300M -> 150M
    },

    "kg-extract-objects" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "graph-rag" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "graph-embeddings" +: {
        "memory-reservation":: "256M",  // 512M -> 256M
    },

    // Structured data services
    "nlp-query" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "structured-query" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

    "structured-diag" +: {
        "memory-reservation":: "48M",   // 96M -> 48M
    },

    // Init service
    "init-trustgraph" +: {
        "memory-reservation":: "64M",   // 128M -> 64M
    },

}
