
# VERSION=$(shell git describe | sed 's/^v//')
VERSION=0.9.3

DOCKER=podman

all: container

CONTAINER=docker.io/trustgraph/trustgraph-flow

container:
	${DOCKER} build -f Containerfile -t ${CONTAINER}:${VERSION} \
	    --format docker

push:
	${DOCKER} push ${CONTAINER}:${VERSION}

start:
	${DOCKER} run -i -t --name ${NAME} \
	    -i -t \
	    -p 8081:8081 \
	    -v $$(pwd)/keys:/keys \
	    -v $$(pwd)/configs:/configs \
	    ${CONTAINER}:${VERSION}

stop:
	${DOCKER} rm -f ${NAME}

clean:
	rm -rf wheels/

set-version:
	echo '"${VERSION}"' > templates/values/version.jsonnet

TEMPLATES=azure bedrock claude cohere mix ollama openai vertexai \
    openai-neo4j storage

DCS=$(foreach template,${TEMPLATES},${template:%=tg-launch-%.yaml})

MODELS=azure bedrock claude cohere ollama openai vertexai
GRAPHS=cassandra neo4j

# tg-launch-%.yaml: templates/%.jsonnet templates/components/version.jsonnet
# 	jsonnet -Jtemplates \
# 	    -S ${@:tg-launch-%.yaml=templates/%.jsonnet} > $@

# VECTORDB=milvus
VECTORDB=qdrant

JSONNET_FLAGS=-J templates -J .


update-templates: set-version
	for graph in ${GRAPHS}; do \
	    cm=$${graph},pulsar,${VECTORDB},grafana; \
	    input=templates/main.jsonnet; \
	    output=tg-storage-$${graph}.yaml; \
	    echo $${graph} '->' $${output}; \
	    jsonnet ${JSONNET_FLAGS} \
	         --ext-str options=$${cm} -S $${input} > $${output}; \
	done
	for model in ${MODELS}; do \
	  for graph in ${GRAPHS}; do \
	    cm=$${graph},pulsar,${VECTORDB},embeddings-hf,graph-rag,grafana,trustgraph,$${model}; \
	    input=templates/main.jsonnet; \
	    output=tg-launch-$${model}-$${graph}.yaml; \
	    echo $${model} + $${graph} '->' $${output}; \
	    jsonnet ${JSONNET_FLAGS} \
	         --ext-str options=$${cm} -S $${input} > $${output}; \
	  done; \
	done

FORCE:

IGNOREconfig.yaml: config.json FORCE
	jsonnet -J . -J templates/ templates/config-to-gcp-k8s.jsonnet | \
	    python3 -c 'import sys, yaml, json; j=json.loads(sys.stdin.read()); print(yaml.safe_dump(j))' > $@

config.yaml: config.json FORCE
	jsonnet -J . -J templates/ templates/config-to-minikube-k8s.jsonnet | \
	    python3 -c 'import sys, yaml, json; j=json.loads(sys.stdin.read()); print(yaml.safe_dump(j))' > $@
