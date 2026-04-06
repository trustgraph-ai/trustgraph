import("../packages/flow/dist/prompt/template.js")
  .then((m) => m.run())
  .catch((err) => {
    console.error(err);
    process.exit(1);
  });
