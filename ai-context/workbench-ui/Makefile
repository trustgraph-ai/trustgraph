
PACKAGE_VERSION=0.0.0
VERSION=0.0.8

all: service-package container

ui:
	npm run build
	rm -rf workbench-ui/workbench/ui/
	cp -r dist/ workbench-ui/workbench/ui/
#	cp public/*.png workbench-ui/workbench/ui/
	cp public/*.svg workbench-ui/workbench/ui/

service-package: ui update-package-versions
	cd workbench-ui && python3 setup.py sdist --dist-dir ../pkgs/

update-package-versions:
	echo __version__ = \"${PACKAGE_VERSION}\" > workbench-ui/workbench/version.py

CONTAINER=docker.io/trustgraph/workbench-ui
DOCKER=podman

container:
	${DOCKER} build -f Containerfile -t ${CONTAINER}:${VERSION} \
	    --format docker

push:
	${DOCKER} push ${CONTAINER}:${VERSION}

docker-hub-login:
	cat docker-token.txt | \
	    docker login -u trustgraph --password-stdin registry-1.docker.io

