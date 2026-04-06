import("../packages/flow/dist/gateway/server.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
