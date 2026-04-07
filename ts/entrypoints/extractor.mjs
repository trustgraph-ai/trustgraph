import("../packages/flow/dist/extract/knowledge-extract.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
