local version = import "version.jsonnet";
{
    cassandra: "docker.io/cassandra:4.1.6",
    neo4j: "docker.io/neo4j:5.22.0-community-bullseye",
    pulsar: "docker.io/apachepulsar/pulsar:3.3.1",
    pulsar_manager: "docker.io/apachepulsar/pulsar-manager:v0.4.0",
    etcd: "quay.io/coreos/etcd:v3.5.15",
    minio: "docker.io/minio/minio:RELEASE.2024-08-17T01-24-54Z",
    milvus: "docker.io/milvusdb/milvus:v2.4.9",
    prometheus: "docker.io/prom/prometheus:v2.53.2",
    grafana: "docker.io/grafana/grafana:11.1.4",
    trustgraph: "docker.io/trustgraph/trustgraph-flow:" + version,
    qdrant: "docker.io/qdrant/qdrant:v1.11.1",
    memgraph_mage: "docker.io/memgraph/memgraph-mage:1.22-memgraph-2.22",
    memgraph_lab: "docker.io/memgraph/lab:2.19.1",
    falkordb: "docker.io/falkordb/falkordb:latest",
    "workbench-ui": "docker.io/trustgraph/workbench-ui:0.1.9",
}
