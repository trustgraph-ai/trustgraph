
# Test Suite for TrustGraph

## Setup for Python

```
pip3 -m venv env
. env/bin/activate
pip3 install -r requirements.txt
```

## Dev mode

```
npm install
npm run dev
```

This runs the application in Vite at http://localhost:5173.
Note that UI bit works, but the generation part isn't running.

## Run it all locally

This builds the UI and the Python package:
```
make service-package
```

Then run the Python package which serves the generator and UI:

```
export PYTHONPATH=workbench-ui
workbench-ui/scripts/service
```

Generation should work

## Run it in a container

Build the container:
```
make service-package VERSION=0.0.0
```

and run it

```
podman run -i -t -p 8080:8080 localhost/workbench-ui:0.0.0
```

Go to http://localhost:8080

## Release it

Deployment is Github actions, automatic to Docker Hub.  Deployment kicks in
automatically on anything with a version tag.  Version tags should be of
form v1.2.3.  Convention is to have a branch name something like
`release/vX.Y` for version tags of the form `vX.Y.Z`.  So,
version `v0.1.10` would be release on branch `release/v0.1`.

On release, container images are pushed to docker hub.

To release with TrustGraph, change the version number of the container
in the trustgraph repo, `templates/values/images.jsonnet` and also
in the config portal repo, same filename, `templates/values/images.jsonnet`.

