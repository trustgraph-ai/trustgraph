The MCP server requires two secrets provided as environment variables. The MCP server secret is used by clients to authenticate to the MCP service. The gateway secret must match the value configured for the API Gateway, as the MCP server acts as a client of the gateway. Both can be set to empty strings to disable authentication.

```
MCP_SERVER_SECRET=
GATEWAY_SECRET=
```
