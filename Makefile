
# VERSION=$(shell git describe | sed 's/^v//')
VERSION=0.7.1

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
# 	sed -i 's/trustgraph-flow:[0-9]*\.[0-9]*\.[0-9]*/trustgraph-flow:'${VERSION}'/' docker-compose*.yaml
	echo '"${VERSION}"' > templates/components/version.jsonnet

TEMPLATES=azure bedrock claude cohere mix ollama openai vertexai \
    openai-neo4j storage

DCS=$(foreach template,${TEMPLATES},${template:%=tg-launch-%.yaml})

update-templates: set-version ${DCS}

tg-launch-%.yaml: templates/%.jsonnet templates/components/version.jsonnet
	jsonnet -S ${@:tg-launch-%.yaml=templates/%.jsonnet} > $@

