
# VERSION=$(shell git describe | sed 's/^v//')
VERSION=0.7.20

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
	echo '"${VERSION}"' > templates/components/version.jsonnet

TEMPLATES=azure bedrock claude cohere mix ollama openai vertexai \
    openai-neo4j storage

DCS=$(foreach template,${TEMPLATES},${template:%=tg-launch-%.yaml})

MODELS=azure bedrock claude cohere ollama openai vertexai
GRAPHS=cassandra neo4j

tg-launch-%.yaml: templates/%.jsonnet templates/components/version.jsonnet
	jsonnet -S ${@:tg-launch-%.yaml=templates/%.jsonnet} > $@

# VECTORDB=milvus
VECTORDB=qdrant

update-templates: set-version
	for graph in ${GRAPHS}; do \
	    cm=$${graph},pulsar,${VECTORDB},grafana; \
	    input=templates/main.jsonnet; \
	    output=tg-storage-$${graph}.yaml; \
	    echo $${graph} '->' $${output}; \
	    jsonnet --ext-str options=$${cm} -S $${input} > $${output}; \
	done
	for model in ${MODELS}; do \
	  for graph in ${GRAPHS}; do \
	    cm=$${graph},pulsar,${VECTORDB},grafana,trustgraph,$${model}; \
	    input=templates/main.jsonnet; \
	    output=tg-launch-$${model}-$${graph}.yaml; \
	    echo $${model} + $${graph} '->' $${output}; \
	    jsonnet --ext-str options=$${cm} -S $${input} > $${output}; \
	  done; \
	done
