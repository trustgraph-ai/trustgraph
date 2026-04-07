import("../packages/flow/dist/query/embeddings/qdrant-graph-service.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
