#!/bin/bash
#
# Preview API documentation in browser
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
    echo "Usage: $0 [rest|websocket|both]"
    echo
    echo "Preview API documentation:"
    echo "  rest      - Preview REST API documentation"
    echo "  websocket - Preview WebSocket API documentation"
    echo "  both      - Preview both (default)"
    echo
    echo "Note: Uses xdg-open to open in default browser"
}

open_browser() {
    local file="$1"
    if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$file" 2>/dev/null &
    elif command -v open >/dev/null 2>&1; then
        open "$file"
    else
        echo "Cannot open browser automatically. Please open manually:"
        echo "  file://$file"
    fi
}

# Check if docs exist
REST_DOC="$SCRIPT_DIR/../docs/api.html"
WS_DOC="$SCRIPT_DIR/../docs/websocket/index.html"

if [[ ! -f "$REST_DOC" ]] && [[ ! -f "$WS_DOC" ]]; then
    echo "Error: Documentation not found. Build first:"
    echo "  ./specs/build-docs.sh"
    exit 1
fi

# Parse command
CMD="${1:-both}"

case "$CMD" in
    rest)
        if [[ ! -f "$REST_DOC" ]]; then
            echo "Error: REST API docs not found. Build first:"
            echo "  ./specs/build-docs.sh"
            exit 1
        fi
        echo "Opening REST API documentation..."
        open_browser "$(realpath "$REST_DOC")"
        ;;
    websocket|ws)
        if [[ ! -f "$WS_DOC" ]]; then
            echo "Error: WebSocket API docs not found. Build first:"
            echo "  ./specs/build-docs.sh"
            exit 1
        fi
        echo "Opening WebSocket API documentation..."
        open_browser "$(realpath "$WS_DOC")"
        ;;
    both)
        if [[ -f "$REST_DOC" ]]; then
            echo "Opening REST API documentation..."
            open_browser "$(realpath "$REST_DOC")"
            sleep 0.5
        fi
        if [[ -f "$WS_DOC" ]]; then
            echo "Opening WebSocket API documentation..."
            open_browser "$(realpath "$WS_DOC")"
        fi
        ;;
    -h|--help)
        show_usage
        exit 0
        ;;
    *)
        echo "Error: Unknown command '$CMD'"
        echo
        show_usage
        exit 1
        ;;
esac

echo "Done!"
