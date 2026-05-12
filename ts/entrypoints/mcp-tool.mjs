import("@effect/platform-bun/BunRuntime")
  .then(async (BunRuntime) => {
    const m = await import("../packages/flow/dist/agent/mcp-tool/service.js");
    BunRuntime.runMain(m.program);
  })
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
