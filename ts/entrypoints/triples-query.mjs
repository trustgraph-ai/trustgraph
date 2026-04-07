import("../packages/flow/dist/query/triples/falkordb-service.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
