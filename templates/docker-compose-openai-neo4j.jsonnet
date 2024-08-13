
local base = import "components/base.jsonnet";
local url = import "components/url.jsonnet";
local images = import "components/images.jsonnet";

local neo4j = import "components/neo4j.jsonnet";
local pulsar = import "components/pulsar.jsonnet";
local milvus = import "components/milvus.jsonnet";
local grafana = import "components/grafana.jsonnet";
local trustgraph = import "components/trustgraph.jsonnet";

local config = neo4j + pulsar + milvus + grafana + trustgraph + {

    services: std.mergePatch(super.services, {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-openai",
		"-p",
		url.pulsar,
		"-k",
		"${OPENAI_KEY}",
	    ],
	},

	"text-completion-rag": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-openai",
		"-p",
		url.pulsar,
		"-k",
		"${OPENAI_KEY}",
		"-i",
		"non-persistent://tg/request/text-completion-rag",
		"-o",
		"non-persistent://tg/response/text-completion-rag-response",
	    ],
	},

	"query-triples": {
	    image: images.trustgraph,
	    command: [
		"triples-query-neo4j",
		"-p",
		url.pulsar,
		"-g",
		"http://neo4j:7474",
	    ],
	},

	"store-triples": {
	    image: images.trustgraph,
	    command: [
		"triples-write-neo4j",
		"-p",
		url.pulsar,
		"-g",
		"http://neo4j:7474",
	    ],
	}

    })
};

std.manifestYamlDoc(config)

