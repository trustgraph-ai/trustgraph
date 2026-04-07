import("../packages/flow/dist/storage/triples/falkordb-service.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
