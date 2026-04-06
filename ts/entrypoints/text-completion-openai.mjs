import("../packages/flow/dist/model/text-completion/openai.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
