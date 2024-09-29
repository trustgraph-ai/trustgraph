
# VERSION=$(shell git describe | sed 's/^v//')
VERSION=0.11.3

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

TEMPLATES=azure bedrock claude cohere mix llamafile ollama openai vertexai \
    openai-neo4j storage

DCS=$(foreach template,${TEMPLATES},${template:%=tg-launch-%.yaml})

MODELS=azure bedrock claude cohere llamafile ollama openai vertexai
GRAPHS=cassandra neo4j

# tg-launch-%.yaml: templates/%.jsonnet templates/components/version.jsonnet
# 	jsonnet -Jtemplates \
# 	    -S ${@:tg-launch-%.yaml=templates/%.jsonnet} > $@

# VECTORDB=milvus
VECTORDB=qdrant

JSONNET_FLAGS=-J templates -J .

# Temporarily going back to how templates were built in 0.9 because this
# is going away in 0.11.

update-templates: update-dcs
# update-minikubes

JSON_TO_YAML=python3 -c 'import sys, yaml, json; j=json.loads(sys.stdin.read()); print(yaml.safe_dump(j))'
# JSON_TO_YAML=cat

update-dcs: set-version
	for graph in ${GRAPHS}; do \
	    cm=$${graph},pulsar,${VECTORDB},grafana; \
	    input=templates/opts-to-docker-compose.jsonnet; \
	    output=tg-storage-$${graph}.yaml; \
	    echo $${graph} '->' $${output}; \
	    jsonnet ${JSONNET_FLAGS} \
	         --ext-str options=$${cm} $${input} | \
	         ${JSON_TO_YAML} > $${output}; \
	done
	for model in ${MODELS}; do \
	  for graph in ${GRAPHS}; do \
	    cm=$${graph},pulsar,${VECTORDB},embeddings-hf,graph-rag,grafana,trustgraph,$${model}; \
	    input=templates/opts-to-docker-compose.jsonnet; \
	    output=tg-launch-$${model}-$${graph}.yaml; \
	    echo $${model} + $${graph} '->' $${output}; \
	    jsonnet ${JSONNET_FLAGS} \
	         --ext-str options=$${cm} $${input} | \
                 ${JSON_TO_YAML} > $${output}; \
	  done; \
	done

update-minikubes: set-version
	rm -rf deploy/minikube
	mkdir -p deploy/minikube
	for model in ${MODELS}; do \
	  for graph in ${GRAPHS}; do \
	    cm=$${graph},pulsar,${VECTORDB},embeddings-hf,graph-rag,grafana,trustgraph,$${model}; \
	    input=templates/opts-to-minikube-k8s.jsonnet; \
	    output=deploy/minikube/tg-launch-$${model}-$${graph}.yaml; \
	    echo $${model} + $${graph} '->' $${output}; \
	    jsonnet ${JSONNET_FLAGS} \
	        --ext-str options=$${cm} $${input} | \
	        ${JSON_TO_YAML} > $${output}; \
	  done; \
	done

docker-hub-login:
	cat docker-token.txt | \
	    docker login -u trustgraph --password-stdin registry-1.docker.io

FORCE:

IGNOREconfig.yaml: config.json FORCE
	jsonnet -J . -J templates/ templates/config-to-gcp-k8s.jsonnet | \
	    python3 -c 'import sys, yaml, json; j=json.loads(sys.stdin.read()); print(yaml.safe_dump(j))' > $@

config.yaml: config.json FORCE
	jsonnet -J . -J templates/ templates/config-to-minikube-k8s.jsonnet | \
	    python3 -c 'import sys, yaml, json; j=json.loads(sys.stdin.read()); print(yaml.safe_dump(j))' > $@
