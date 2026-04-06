import("../packages/flow/dist/flow-manager/service.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
