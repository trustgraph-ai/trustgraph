// Will work once the agent service is merged.
import("@effect/platform-bun/BunRuntime")
  .then(async (BunRuntime) => {
    const m = await import("../packages/flow/dist/agent/react/service.js");
    BunRuntime.runMain(m.program);
  })
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
