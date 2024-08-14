local version = import "version.jsonnet";
{
    cassandra: "docker.io/cassandra:4.1.5",
    neo4j: "docker.io/neo4j:5.22.0-community-bullseye",
    pulsar: "docker.io/apachepulsar/pulsar:3.3.0",
    pulsar_manager: "docker.io/apachepulsar/pulsar-manager:v0.3.0",
    etcd: "quay.io/coreos/etcd:v3.5.5",
    minio: "docker.io/minio/minio:RELEASE.2024-07-04T14-25-45Z",
    milvus: "docker.io/milvusdb/milvus:v2.4.5",
    prometheus: "docker.io/prom/prometheus:v2.53.1",
    grafana: "docker.io/grafana/grafana:10.0.0",
    trustgraph: "docker.io/trustgraph/trustgraph-flow:" + version,
}
