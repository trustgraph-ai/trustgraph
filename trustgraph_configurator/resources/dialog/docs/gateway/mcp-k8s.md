The MCP server requires two secrets provided in a Kubernetes secret. The MCP server secret is used by clients to authenticate to the MCP service. The gateway secret must match the value configured for the API Gateway, as the MCP server acts as a client of the gateway. Both can be set to empty strings to disable authentication.

```bash
kubectl -n {{namespace}} create secret \
    generic mcp-server-secret \
    --from-literal=mcp-server-secret= \
    --from-literal=gateway-secret=
```
