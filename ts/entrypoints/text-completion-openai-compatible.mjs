import("../packages/flow/dist/model/text-completion/openai-compatible.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
