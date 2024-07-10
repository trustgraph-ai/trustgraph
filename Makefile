
# VERSION=$(shell git describe | sed 's/^v//')
VERSION=0.1.16

all: container

CONTAINER=docker.io/trustgraph/trustgraph-flow

container:
	podman build -f Containerfile -t ${CONTAINER}:${VERSION} \
	    --format docker

push:
	podman push ${CONTAINER}:${VERSION}

start:
	podman run -i -t --name ${NAME} \
	    -i -t \
	    -p 8081:8081 \
	    -v $$(pwd)/keys:/keys \
	    -v $$(pwd)/configs:/configs \
	    ${CONTAINER}:${VERSION}

stop:
	podman rm -f ${NAME}

clean:
	rm -rf wheels/

# sed -i 's/0.1.15/0.1.16/' docker-compose*.yaml
