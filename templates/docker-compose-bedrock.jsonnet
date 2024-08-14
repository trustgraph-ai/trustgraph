
local cassandra = import "components/cassandra.jsonnet";
local pulsar = import "components/pulsar.jsonnet";
local milvus = import "components/milvus.jsonnet";
local grafana = import "components/grafana.jsonnet";
local trustgraph = import "components/trustgraph.jsonnet";
local bedrock = import "components/bedrock.jsonnet";

local config = cassandra + pulsar + milvus + grafana + trustgraph + bedrock;

std.manifestYamlDoc(config)

