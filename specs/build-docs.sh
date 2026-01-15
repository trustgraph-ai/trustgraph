#!/bin/bash
#
# Build documentation from OpenAPI and AsyncAPI specifications
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Building TrustGraph API Documentation..."
echo

# Create output directory
mkdir -p ../docs

# Build REST API documentation
echo "Building REST API documentation (OpenAPI)..."
cd api
npx --yes @redocly/cli build-docs openapi.yaml -o ../../docs/api.html
echo "✓ REST API docs generated: docs/api.html"
echo

# Build WebSocket API documentation
echo "Building WebSocket API documentation (AsyncAPI)..."
cd ../websocket
npx --yes -p @asyncapi/cli asyncapi generate fromTemplate asyncapi.yaml @asyncapi/html-template@3.0.0 -o ../../docs/websocket --force-write
echo "✓ WebSocket API docs generated: docs/websocket/index.html"
echo

cd "$SCRIPT_DIR"
echo "Documentation build complete!"
echo
echo "View documentation:"
echo "  REST API:      file://$(realpath ../docs/api.html)"
echo "  WebSocket API: file://$(realpath ../docs/websocket/index.html)"
