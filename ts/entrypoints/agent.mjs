// Will work once the agent service is merged.
import("../packages/flow/dist/agent/react/service.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
