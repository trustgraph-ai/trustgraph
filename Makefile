
# VERSION=$(shell git describe | sed 's/^v//')
VERSION=0.6.0

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
	echo '"${VERSION}"' > templates/version.jsonnet

TEMPLATES=azure bedrock claude cohere mix ollama openai vertexai
DCS=$(foreach template,${TEMPLATES},${template:%=docker-compose-%.yaml})

update-templates: set-version ${DCS}

docker-compose-%.yaml: templates/docker-compose-%.jsonnet templates/version.jsonnet
	jsonnet -S ${@:docker-compose-%.yaml=templates/docker-compose-%.jsonnet} > $@

