
# VERSION=$(shell git describe | sed 's/^v//')
VERSION=0.12.0

DOCKER=podman

all: container

# Not used
wheels:
	pip3 wheel --no-deps --wheel-dir dist trustgraph-base/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-flow/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-vertexai/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-bedrock/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-parquet/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-embeddings-hf/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-cli/

packages: update-package-versions
	rm -rf dist/
	cd trustgraph-base && python3 setup.py sdist --dist-dir ../dist/
	cd trustgraph-flow && python3 setup.py sdist --dist-dir ../dist/
	cd trustgraph-vertexai && python3 setup.py sdist --dist-dir ../dist/
	cd trustgraph-bedrock && python3 setup.py sdist --dist-dir ../dist/
	cd trustgraph-parquet && python3 setup.py sdist --dist-dir ../dist/
	cd trustgraph-embeddings-hf && python3 setup.py sdist --dist-dir ../dist/
	cd trustgraph-cli && python3 setup.py sdist --dist-dir ../dist/

pypi-upload:
	twine upload dist/*-${VERSION}.*

CONTAINER=docker.io/trustgraph/trustgraph-flow

update-package-versions:
	mkdir -p trustgraph-cli/trustgraph
	echo __version__ = \"${VERSION}\" > trustgraph-base/trustgraph/base_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-flow/trustgraph/flow_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-vertexai/trustgraph/vertexai_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-bedrock/trustgraph/bedrock_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-parquet/trustgraph/parquet_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-embeddings-hf/trustgraph/embeddings_hf_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-cli/trustgraph/cli_version.py

container: update-package-versions
	${DOCKER} build -f Containerfile -t ${CONTAINER}:${VERSION} \
	    --format docker

push:
	${DOCKER} push ${CONTAINER}:${VERSION}

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

JSON_TO_YAML=python3 -c 'import sys, yaml, json; j=json.loads(sys.stdin.read()); print(yaml.safe_dump(j))'

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

docker-hub-login:
	cat docker-token.txt | \
	    docker login -u trustgraph --password-stdin registry-1.docker.io

