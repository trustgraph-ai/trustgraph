import("../packages/flow/dist/agent/mcp-tool/service.js")
  .then((m) => m.McpToolService.launch("mcp-tool"))
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
