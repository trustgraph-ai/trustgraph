#!/usr/bin/env bash
# Start the Brave Search MCP server with HTTP transport.
#
# Usage: ./scripts/run-brave-mcp.sh
#
# Requires:
#   - @brave/brave-search-mcp-server (npx will auto-install)
#   - BRAVE_API_KEY env var or 1Password access

set -euo pipefail

# Resolve API key from env or 1Password
if [ -z "${BRAVE_API_KEY:-}" ]; then
  if command -v op &>/dev/null; then
    BRAVE_API_KEY="$(op read 'op://beep-dev-secrets/beep-ai/BRAVE_API_KEY')"
    echo "[brave-mcp] Loaded API key from 1Password"
  else
    echo "[brave-mcp] ERROR: BRAVE_API_KEY not set and 'op' CLI not found"
    exit 1
  fi
fi

echo "[brave-mcp] Starting Brave Search MCP server on port 8383..."
exec npx --yes @brave/brave-search-mcp-server \
  --brave-api-key "$BRAVE_API_KEY" \
  --transport http \
  --port 8383 \
  --stateless true
