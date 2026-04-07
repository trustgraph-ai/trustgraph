import("../packages/flow/dist/storage/embeddings/graph-embeddings-service.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
