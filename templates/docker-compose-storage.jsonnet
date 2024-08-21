
local cassandra = import "components/stores/cassandra.jsonnet";
local pulsar = import "components/pulsar.jsonnet";
local milvus = import "components/stores/milvus.jsonnet";
local grafana = import "components/grafana.jsonnet";

local config = cassandra + pulsar + milvus + grafana;

std.manifestYamlDoc(config)

