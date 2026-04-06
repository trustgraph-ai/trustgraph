import("../packages/flow/dist/embeddings/ollama.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
