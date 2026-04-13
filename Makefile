
# VERSION=$(shell git describe | sed 's/^v//')

VERSION=0.0.0

DOCKER=podman

all: containers

# Not used
wheels:
	pip3 wheel --no-deps --wheel-dir dist trustgraph/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-base/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-flow/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-vertexai/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-bedrock/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-embeddings-hf/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-cli/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-ocr/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-unstructured/
	pip3 wheel --no-deps --wheel-dir dist trustgraph-mcp/

packages: update-package-versions
	rm -rf dist/
	cd trustgraph && python -m build --sdist --outdir ../dist/
	cd trustgraph-base && python -m build --sdist --outdir ../dist/
	cd trustgraph-flow && python -m build --sdist --outdir ../dist/
	cd trustgraph-vertexai && python -m build --sdist --outdir ../dist/
	cd trustgraph-bedrock && python -m build --sdist --outdir ../dist/
	cd trustgraph-embeddings-hf && python -m build --sdist --outdir ../dist/
	cd trustgraph-cli && python -m build --sdist --outdir ../dist/
	cd trustgraph-ocr && python -m build --sdist --outdir ../dist/
	cd trustgraph-unstructured && python -m build --sdist --outdir ../dist/
	cd trustgraph-mcp && python -m build --sdist --outdir ../dist/

pypi-upload:
	twine upload dist/*-${VERSION}.*

CONTAINER_BASE=docker.io/trustgraph

update-package-versions:
	mkdir -p trustgraph-cli/trustgraph
	mkdir -p trustgraph/trustgraph
	echo __version__ = \"${VERSION}\" > trustgraph-base/trustgraph/base_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-flow/trustgraph/flow_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-vertexai/trustgraph/vertexai_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-bedrock/trustgraph/bedrock_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-embeddings-hf/trustgraph/embeddings_hf_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-cli/trustgraph/cli_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-ocr/trustgraph/ocr_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-unstructured/trustgraph/unstructured_version.py
	echo __version__ = \"${VERSION}\" > trustgraph/trustgraph/trustgraph_version.py
	echo __version__ = \"${VERSION}\" > trustgraph-mcp/trustgraph/mcp_version.py

containers: container-base container-flow \
container-bedrock container-vertexai \
container-hf container-ocr \
container-unstructured container-mcp

some-containers: container-base container-flow

push:
	${DOCKER} push ${CONTAINER_BASE}/trustgraph-base:${VERSION}
	${DOCKER} push ${CONTAINER_BASE}/trustgraph-flow:${VERSION}
	${DOCKER} push ${CONTAINER_BASE}/trustgraph-bedrock:${VERSION}
	${DOCKER} push ${CONTAINER_BASE}/trustgraph-vertexai:${VERSION}
	${DOCKER} push ${CONTAINER_BASE}/trustgraph-hf:${VERSION}
	${DOCKER} push ${CONTAINER_BASE}/trustgraph-ocr:${VERSION}
	${DOCKER} push ${CONTAINER_BASE}/trustgraph-unstructured:${VERSION}
	${DOCKER} push ${CONTAINER_BASE}/trustgraph-mcp:${VERSION}

# Individual container build targets
container-%: update-package-versions
	${DOCKER} build \
	    -f containers/Containerfile.${@:container-%=%} \
	    -t ${CONTAINER_BASE}/trustgraph-${@:container-%=%}:${VERSION} .

# Individual container build targets
manifest-%: update-package-versions
	-@${DOCKER} manifest rm \
	    ${CONTAINER_BASE}/trustgraph-${@:manifest-%=%}:${VERSION}
	${DOCKER} build --platform linux/amd64,linux/arm64 \
	    -f containers/Containerfile.${@:manifest-%=%} \
	    --manifest \
	    ${CONTAINER_BASE}/trustgraph-${@:manifest-%=%}:${VERSION} .

# Push a container
push-container-%:
	${DOCKER} push \
	    ${CONTAINER_BASE}/trustgraph-${@:push-container-%=%}:${VERSION}

# Push a manifest
push-manifest-%:
	${DOCKER} manifest push \
	    ${CONTAINER_BASE}/trustgraph-${@:push-manifest-%=%}:${VERSION}

clean:
	rm -rf wheels/

set-version:
	echo '"${VERSION}"' > templates/values/version.jsonnet

docker-hub-login:
	cat docker-token.txt | \
	    ${DOCKER} login -u trustgraph --password-stdin registry-1.docker.io

