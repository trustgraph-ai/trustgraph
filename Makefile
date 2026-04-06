
PACKAGE_VERSION=0.0.0
VERSION=0.0.0

all: container

package: update-package-versions
	python3 -m build --sdist --outdir pkgs

update-package-versions:
	echo __version__ = \"${PACKAGE_VERSION}\" > trustgraph_configurator/version.py

CONTAINER=localhost/config-svc
DOCKER=podman

container:
	${DOCKER} build -f Containerfile -t ${CONTAINER}:${VERSION} \
	    --format docker

# On port 8081
run-container:
	${DOCKER} run -i -t -p 8081:8080 ${CONTAINER}:${VERSION}
