import("../packages/flow/dist/retrieval/document-rag-service.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
