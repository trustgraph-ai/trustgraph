import("@effect/platform-bun/BunRuntime")
  .then(async (BunRuntime) => {
    const m = await import("../packages/flow/dist/query/triples/falkordb-service.js");
    BunRuntime.runMain(m.program);
  })
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
